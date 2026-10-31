"""Register the targeted reset-delay ECO for traceable final A."""
from librelane.steps import Step
from librelane.steps.odb import InsertECOBuffers
from pathlib import Path

@Step.factory.register()
class ResetIncrementalA(InsertECOBuffers):
    id='Custom.ResetIncrementalA'
    name='Preserve traceable A and repair reset removal'
    def get_script_path(self):
        return '/work/scripts/reset_incremental_a.py'
    def get_command(self):
        return super().get_command()+['--odbpy-scripts',str(Path(InsertECOBuffers.get_script_path(self)).parent)]

if __name__=='__main__':
    from librelane.steps.__main__ import cli
    cli()
