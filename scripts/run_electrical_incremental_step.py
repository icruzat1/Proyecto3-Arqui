"""Register the project-local incremental ECO with LibreLane's step runner."""
from librelane.steps import Step
from librelane.steps.odb import InsertECOBuffers
from pathlib import Path

@Step.factory.register()
class ElectricalIncremental(InsertECOBuffers):
    id='Custom.ElectricalIncremental'
    name='Targeted electrical ECO with preserved routes'
    def get_script_path(self):
        return '/work/scripts/electrical_incremental_b.py'
    def get_command(self):
        return super().get_command()+['--odbpy-scripts',str(Path(InsertECOBuffers.get_script_path(self)).parent)]

if __name__=='__main__':
    from librelane.steps.__main__ import cli
    cli()
