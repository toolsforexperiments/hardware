'''
A simple driver to control the homemade current source
'''

__author__ = "Kaushik Singirikonda"
__email__ = 'ks105@illinois.edu'

from functools import partial
from typing import Optional, Union, Any
import time,sys
import clr  # install pythonnet

from qcodes.instrument.parameter import DelegateParameter
from qcodes import (Instrument, validators as vals)
from qcodes.instrument.channel import InstrumentChannel
from qcodes.utils.validators import Numbers, Bool, Enum, Ints

'''
In order to initiate the use of the current source, follow the guidelines given here :

https://uillinoisedu.sharepoint.com/sites/Pfafflab/_layouts/OneNote.aspx?id=%2Fsites%2FPfafflab%2FSiteAssets%2FPfafflab%20Notebook&wd=target%28Projects%2FElementaryCircuits%2FCurrent%20Source.one%7C8C1A05E0-ED99-4899-83F1-97F9EB59041F%2F%29
onenote:https://uillinoisedu.sharepoint.com/sites/Pfafflab/SiteAssets/Pfafflab%20Notebook/Projects/ElementaryCircuits/Current%20Source.one#section-id={8C1A05E0-ED99-4899-83F1-97F9EB59041F}&end
'''


class AD5760(Instrument):

    def __init__(self, name: str, host_name: str, path: str, syspath: str, terminator: str = "\n",
                 **kwargs: Any) -> None:
        super().__init__(name, **kwargs)
        self.connect_board(host_name, path, syspath)

        self.add_parameter('output',
                           label='Output State',
                           get_cmd=self.state,
                           set_cmd=lambda x: self.on() if x else self.off(),
                           val_mapping={
                               'off': 0,
                               'on': 1,
                           })
        
        self.add_parameter('voltage',
                           label='Voltage',
                           unit='V',
                           set_cmd=self._get_set_volt,
                           get_cmd=self._get_volt,
                           vals= Numbers(min_value=-10, max_value=10)
                           )
        
    def on(self) -> None:
        self.write('OUTPUT 1')
        self.measure._output = True
        
    def off(self) -> None:
        self.write('OUTPUT 0')
        self.measure._output = False

    def state(self):
        state = self.ask()
        if state is not None:
            return bool(1)
        else:
            return bool(0)
    
    def connect_board(self, host_name: str, path: str, syspath: str):
        
        sys.path.append(rf'{syspath}')

        clr.AddReference('AnalogDevices.Csa.Remoting.Clients')
        clr.AddReference('AnalogDevices.Csa.Remoting.Contracts')
        
        # noinspection PyUnresolvedReferences,SpellCheckingInspection
        from AnalogDevices.Csa.Remoting.Clients import ClientManager  #noqa
        manager = ClientManager.Create(-1)
        self.client = manager.CreateRequestClient(f"localhost:{host_name}")
        self.client.ContextPath = path
        self.client.WriteRegister("2", "786")
        
    def _get_set_volt(self,
                        output_level: Optional[float] = None
                        ) -> Optional[float]:
        """
        Get or set the output level.

        Args:
            mode: "CURR" or "VOLT"
            output_level: If missing, we assume that we are getting the
                current level. Else we are setting it
        """
        if output_level is not None:
            self.write(output_level)
            return None
        return self.ask()

        
    def ramp_voltage(self, ramp_to: float, step: float, delay: float) -> None:
        """
        Ramp the voltage from the current level to the specified output.

        Args:
            ramp_to: The ramp target in Volt
            step: The ramp steps in Volt
            delay: The time between finishing one step and
                starting another in seconds.
        """

        self.ramp_trial(ramp_to, step, delay)


    def ramp_trial(self, ramp_to: float, step: float, delay: float):
        
        v_in = self.voltage()
        v_f = v_in
        if ramp_to > v_in:
            num_steps = (ramp_to - v_in)/step +1
            for i in range(int(num_steps+1)):
                v_f += step
                self.voltage(v_f)
                time.sleep(delay)
        elif ramp_to < v_in:
            num_steps = - (ramp_to - v_in)/step 
            for i in range(int(num_steps+1)):
                v_f -= step
                self.voltage(v_f)
                time.sleep(delay) 

    def _get_volt(self):
        return self.ask()

    def _set_output(self, output_level) -> None:
        self.write()
        
    def ask(self):
        return (float(int(self.client.ReadRegister("1"), 16))-524288)*20/1048576
    
    def write(self, output_level):
        output_conv = int((output_level + 10)*65536/20)
        self.client.WriteRegister("1", str(output_conv))
        
