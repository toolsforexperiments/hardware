'''
A simple driver to control the AD5760 current source
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
To use this current source, you first have to install and setup the ACE software. Upon connecting to the AD5760
board with your computer using the software, you have to initialize a setup on python to talk to the software to
enable writing.

Following this, you can simply run this code to operate a stable current source.


'''


class AD5760(Instrument):

    def __init__(self, name: str, host_name: str, path: str, syspath: str, terminator: str = "\n",
                 **kwargs: Any) -> None:
        
        '''
        path:  syspath is the path of the specific device that we want to talk to using the app.
        This path indicates the specific type of device that we want to talk to and the specific 
        subsystem as well.
        for example "\System\Subsystem_1\EVAL-AD5760SDZ\AD5760"

        syspath:
        this is the address of the ACE application, using which we talk to the current source through 
        python. for example "C:\Program Files\Analog Devices\ACE\Client"
        '''
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
        
        self.add_parameter('current',
                           label='Current',
                           unit='A',
                           set_cmd=self._get_set_current,
                           get_cmd=self._get_current,
                           vals= Numbers(min_value=-0.1, max_value=0.1))
        
    def on(self) -> None:
        self.write('OUTPUT 1')
        self.measure._output = True
        
    def off(self) -> None:
        self.write('OUTPUT 0')
        self.measure._output = False

    def state(self):
        try:
            self.ask()
            return True
        except:
            return False
    
    def connect_board(self, host_name: str, path: str, syspath: str):
        
        sys.path.append(rf'{syspath}')

        clr.AddReference('AnalogDevices.Csa.Remoting.Clients')
        clr.AddReference('AnalogDevices.Csa.Remoting.Contracts')
        
        from AnalogDevices.Csa.Remoting.Clients import ClientManager  
        manager = ClientManager.Create(-1)
        self.client = manager.CreateRequestClient(f"localhost:{host_name}")
        self.client.ContextPath = path
        self.client.WriteRegister("2", "786")
        
    def _get_set_volt(self,
                        output_level: Optional[float] = None
                        ) -> Optional[float]:
        """
        Get or set the voltage output.

        Args:
            output_level: If missing, we assume that we are getting the
                voltage output. Else we are setting it
        """
        if output_level is not None:
            self.write(output_level)
            return None
        return self.ask()
    
    def _get_set_current(self,
                      output_level: Optional[float] = None
                      ) -> Optional[float]:
        
        """
        Get or set the current output.

        Args:
            output_level: If missing, we assume that we are getting the
                current output. Else we are setting it
        """

        if output_level is not None:
            self.write(output_level*100)
            return None
        return self.ask()/100
    
    
    def ramp_current(self, ramp_to: float, step: float, delay: float) -> None:
        """
        Ramp the current from the current level to the specified output.

        Args:
            ramp_to: The ramp target in Amps
            step: The ramp steps in Amps
            delay: The time between finishing one step and
                starting another in seconds.
        """
        self.ramp_trial(ramp_to*100, step*100, delay)

        
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
    
    def _get_current(self):
        return self.ask()/100

    def _set_output(self, output_level) -> None:
        self.write()
        
    def ask(self):
        '''
        More features to be added,

        As the device operates in hexadecimals, we convert the output to an integer type variable.
        Following which, the range of the output is adjusted by converting the allowed range of outputs
        to measureable values.
        '''
        return (float(int(self.client.ReadRegister("1"), 16))-524288)*20/1048576
    
    def write(self, output_level):
        output_conv = int((output_level + 10)*65536/20)
        self.client.WriteRegister("1", str(output_conv))
        
