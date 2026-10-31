"""Local reset delay ECO on traceable A; no RTL or original placement changes."""
import json,sys
sys.dont_write_bytecode=True
i=sys.argv.index('--odbpy-scripts')
sys.path.insert(0,sys.argv[i+1]); del sys.argv[i:i+2]
from reader import click_odb,click,odb
import grt as GRT

@click.command()
@click_odb
def cli(reader):
    block=reader.block
    master=reader.db.findMaster('gf180mcu_fd_sc_mcu7t5v0__dlyb_1')
    assert master
    originals={i.getName():i for i in block.getInsts()}
    aliases={}
    def snapshot(normalize=False):
        return sorted([i.getName(),i.getMaster().getName(),list(i.getLocation()),str(i.getOrient()),
                       sorted([t.getMTerm().getName(),aliases.get(t.getNet().getName(),t.getNet().getName()) if normalize else t.getNet().getName()]
                              for t in i.getITerms() if t.getNet())] for i in originals.values())
    before=snapshot()
    loads=[block.findInst(n).findITerm('RN') for n in ['u_reset._2_','u_reset._3_']]
    net=loads[0].getNet()
    assert net.getName()=='net936' and loads[1].getNet().getName()==net.getName()
    assert not list(net.getBTerms())
    inputs=[t for t in net.getITerms() if t.isInputSignal()]
    assert {t.getInst().getName()+'/'+t.getMTerm().getName() for t in inputs}=={'u_reset._2_/RN','u_reset._3_/RN'}
    assert block.findInst('hold937').findITerm('Z').getNet().getName()==net.getName()
    statuses=[(i,i.getPlacementStatus()) for i in originals.values()]
    for i,_ in statuses:i.setPlacementStatus('LOCKED')
    router=reader.design.getGlobalRouter();reader._grt_setup(router)
    inc=GRT.IncrementalGRoute(router,block)
    name='eco13_reset_delay'
    assert block.findInst(name) is None and block.findNet(name+'_net') is None
    inst=odb.dbInst.create(block,master,name);branch=odb.dbNet.create(block,name+'_net')
    xy=[t.getInst().getLocation() for t in loads]
    inst.setOrient('R0');inst.setLocation(*(sum(p[k] for p in xy)//len(xy) for k in [0,1]));inst.setPlacementStatus('PLACED')
    inst.findITerm('I').connect(net);inst.findITerm('Z').connect(branch)
    for t in loads:t.connect(branch)
    aliases[branch.getName()]=net.getName()
    router.addDirtyNet(net);router.addDirtyNet(branch)
    site=reader.rows[0].getSite()
    dx=int(reader.design.micronToDBU(reader.config['PL_MAX_DISPLACEMENT_X'])/site.getWidth())
    dy=int(reader.design.micronToDBU(reader.config['PL_MAX_DISPLACEMENT_Y'])/site.getHeight())
    reader.design.getOpendp().detailedPlacement(dx,dy)
    inc.updateRoutes(True)
    for i,s in statuses:i.setPlacementStatus(s)
    assert snapshot(True)==before,'Original placement/connectivity changed beyond inserted non-inverting delay'
    alu=[n for n in originals if n.startswith('u_soc.u_core.u_id.u_alu.')]
    assert len(alu)==589
    print('VERIFIED_RESET_ECO '+json.dumps(dict(instance=name,master=master.getName(),source_net=net.getName(),
        loads=['u_reset._2_/RN','u_reset._3_/RN'],alu_cells_preserved=len(alu),
        original_instances_preserved=len(originals),modified_signal_nets=2)),flush=True)

if __name__=='__main__':cli()
