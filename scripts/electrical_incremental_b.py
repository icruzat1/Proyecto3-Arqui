"""Incremental ECO using LibreLane's ODB reader and global-route callbacks.

Placement locking and IncrementalGRoute follow LibreLane eco_buffer.py
(Apache-2.0, Efabless Corporation). Preserve existing original placement and
collapse new identity buffers to verify original connectivity.
"""
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
index = sys.argv.index('--odbpy-scripts')
sys.path.insert(0, sys.argv[index+1])
del sys.argv[index:index+2]
from reader import click_odb, click, odb
import grt as GRT

@click.command()
@click_odb
def cli(reader):
    block = reader.block
    master = reader.db.findMaster('gf180mcu_fd_sc_mcu7t5v0__buf_4')
    assert master
    originals = {i.getName(): i for i in block.getInsts()}
    aliases = {}
    def snapshot(normalize=False):
        return sorted([i.getName(),i.getMaster().getName(),list(i.getLocation()),
                       str(i.getOrient()),str(i.getPlacementStatus()),
                       sorted([t.getMTerm().getName(),aliases.get(t.getNet().getName(),t.getNet().getName()) if normalize else t.getNet().getName()]
                              for t in i.getITerms() if t.getNet())] for i in originals.values())
    before = snapshot()
    statuses = [(i,i.getPlacementStatus()) for i in originals.values()]
    for i,_ in statuses: i.setPlacementStatus('LOCKED')
    router = reader.design.getGlobalRouter()
    reader._grt_setup(router)
    inc = GRT.IncrementalGRoute(router,block)
    created = []
    def center(terms):
        xy = [t.getInst().getLocation() for t in terms]
        return tuple(sum(p[k] for p in xy)//len(xy) for k in [0,1])
    def create(name, at):
        assert block.findInst(name) is None and block.findNet(name+'_net') is None
        inst = odb.dbInst.create(block,master,name)
        net = odb.dbNet.create(block,name+'_net')
        inst.setOrient('R0');inst.setLocation(*at);inst.setPlacementStatus('PLACED')
        return inst,net
    # Buffer the remaining NOR4 output: its Boolean function is unchanged.
    driver = block.findInst('u_soc.u_core.u_rf._1646_').findITerm('ZN')
    assert driver.getInst().getMaster().getName().endswith('__nor4_2')
    oldnet = driver.getNet()
    buf,shortnet = create('eco12_rf_driver',driver.getInst().getLocation())
    driver.connect(shortnet);buf.findITerm('I').connect(shortnet);buf.findITerm('Z').connect(oldnet)
    aliases[shortnet.getName()] = oldnet.getName()
    router.addDirtyNet(oldnet);router.addDirtyNet(shortnet)
    created.append(dict(buffer=buf.getName(),kind='driver',source=oldnet.getName()))
    for name in ['fanout1716','fanout2160']:
        net = block.findInst(name).findITerm('Z').getNet()
        loads = [t for t in net.getITerms() if t.isInputSignal()]
        assert len(loads)==11 and not list(net.getBTerms()),(name,len(loads))
        def pos(t):return t.getInst().getLocation()
        logic = [t for t in loads if 'antenna' not in t.getInst().getMaster().getName()]
        units = {t.getInst().getName()+'/'+t.getMTerm().getName():[t] for t in logic}
        for t in loads:
            if t in logic:continue
            near = min(logic,key=lambda x:sum(abs(a-b) for a,b in zip(pos(x),pos(t))))
            units[near.getInst().getName()+'/'+near.getMTerm().getName()].append(t)
        pending = sorted(units.values(),key=lambda u:pos(u[0]))
        number = 0
        while pending:
            group = pending.pop(0)
            while pending:
                fitting = [u for u in pending if len(u)+len(group)<=7]
                if not fitting:break
                nearest = min(fitting,key=lambda u:sum(abs(a-b) for a,b in zip(pos(u[0]),pos(group[0]))))
                pending.remove(nearest);group+=nearest
            assert len(group)<=7
            buf,branch = create(f'eco12_{name}_{number}',center(group))
            buf.findITerm('I').connect(net);buf.findITerm('Z').connect(branch)
            for t in group:t.connect(branch)
            aliases[branch.getName()] = net.getName()
            router.addDirtyNet(net);router.addDirtyNet(branch)
            created.append(dict(buffer=buf.getName(),kind='branch',source=net.getName(),loads=len(group)))
            number+=1
    site=reader.rows[0].getSite()
    dx=int(reader.design.micronToDBU(reader.config['PL_MAX_DISPLACEMENT_X'])/site.getWidth())
    dy=int(reader.design.micronToDBU(reader.config['PL_MAX_DISPLACEMENT_Y'])/site.getHeight())
    reader.design.getOpendp().detailedPlacement(dx,dy)
    inc.updateRoutes(True)
    for i,s in statuses:i.setPlacementStatus(s)
    assert snapshot(True)==before,'Original connectivity/placement changed beyond identity buffers'
    print('VERIFIED_INCREMENTAL_ECO '+json.dumps(created),flush=True)

if __name__=='__main__':cli()
