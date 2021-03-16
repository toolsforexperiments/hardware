
# MJH 2015_10_15.. Maybe this will work??
#Additions by Alex
#average method by Erick Brindock  7/15/16
#driver rewritten by Ryan Kaufman 06/11/20 for Qcodes
#YR: also, here is keysights manual,http://ena.support.keysight.com/e5071c/manuals/webhelp/eng/
#you want the programming -> remote control part for VISA commands

import visa
import types
import logging
import numpy as np
import time
from qcodes import (Instrument, VisaInstrument,
                    ManualParameter, MultiParameter,
                    validators as vals)
#from pyvisa.visa_exceptions import VisaIOError
#triggered=[False]*159 

class Agilent_ENA_5071C(VisaInstrument):
    '''
    This is the driver for the Agilent E5071C Vector Netowrk Analyzer

    Usage:
    Initialize with
    <name> = instruments.create('<name>', 'Agilent_E5071C', 
    address='<GBIP address>, reset=<bool>')
    '''
    
    def __init__(self, name, address = None, **kwargs):
        '''
        Initializes the Agilent_E5071C, and communicates with the wrapper.

        Input:
          name (string)    : name of the instrument
          address (string) : GPIB address
          reset (bool)     : resets to default values, default=False
        '''
        if address == None: 
            raise Exception('TCP IP address needed')
        logging.info(__name__ + ' : Initializing instrument Agilent_E5071C')
        super().__init__(name, address, terminator = '\n', **kwargs)

        # Add in parameters
        self.add_parameter('fstart', 
                          get_cmd = ':SENS1:FREQ:STAR?', 
                          set_cmd = ':SENS1:FREQ:STAR {}', 
                          vals = vals.Numbers(), 
                          get_parser = float, 
                          unit = 'Hz'
                          )
        self.add_parameter('fstop', 
                          get_cmd = ':SENS1:FREQ:STOP?', 
                          set_cmd = ':SENS1:FREQ:STOP {}', 
                          vals = vals.Numbers(), 
                          get_parser = float, 
                          unit = 'Hz'
                          )
        self.add_parameter('fcenter', 
                          get_cmd = ':SENS1:FREQ:CENT?', 
                          set_cmd = ':SENS1:FREQ:CENT {}', 
                          vals = vals.Numbers(), 
                          get_parser = float, 
                          unit = 'Hz'
                          )
        self.add_parameter('fspan', 
                          get_cmd = ':SENS1:FREQ:SPAN?', 
                          set_cmd = ':SENS1:FREQ:SPAN {}', 
                          vals = vals.Numbers(), 
                          get_parser = float, 
                          unit = 'Hz'
                          )
        
        self.add_parameter('rfout', 
                           get_cmd = ':OUTP?',
                           set_cmd = ':OUTP {}',
                           vals = vals.Ints(0,1), 
                           get_parser = int
                           )
        
        self.add_parameter('num_points', 
                           get_cmd = ':SENS1:SWE:POIN?', 
                           set_cmd = ':SENS1:SWE:POIN {}', 
                           vals = vals.Ints(1,1601), 
                           get_parser = int
                           )
        self.add_parameter('ifbw', 
                           get_cmd = ':SENS1:BWID?', 
                           set_cmd = ':SENS1:BWID {}', 
                           vals = vals.Numbers(10,1.5e6),
                           get_parser = float)
        self.add_parameter('power', 
                           get_cmd = ":SOUR1:POW?", 
                           set_cmd = ":SOUR1:POW {}", 
                           unit = 'dBm', 
                           get_parser = float,
                           vals = vals.Numbers(-85, 10)
                           )
        self.add_parameter('power_start',
                           get_cmd = ':SOUR1:POW:STAR?',
                           set_cmd = ':SOUR1:POW:STAR {}',
                           unit = 'dBm',
                           get_parser = float, 
                           vals = vals.Numbers(-85, 10)
                           )
        self.add_parameter('power_stop', 
                           get_cmd = ':SOUR:POW:STOP?', 
                           set_cmd = ':SOUR1:POW:STOP {}', 
                           unit = 'dBm', 
                           get_parser = float, 
                           vals = vals.Numbers(-85, 10)), 
        self.add_parameter('averaging', 
                           get_cmd = ':SENS1:AVER?',
                           set_cmd = ':SENS1:AVER {}', 
                           get_parser = int, 
                           vals = vals.Ints(0,1)
                           )
        self.add_parameter('average_trigger', 
                           get_cmd = ':TRIG:AVER?',
                           set_cmd = ':TRIG:AVER {}', 
                           get_parser = int, 
                           vals = vals.Ints(0,1)
                           )
        self.add_parameter('avgnum', 
                           get_cmd = ':SENS1:AVER:COUN?', 
                           set_cmd = ':SENS1:AVER:COUN {}', 
                           vals = vals.Ints(1), 
                           get_parser = int
                           )
        self.add_parameter('phase_offset', 
                           get_cmd = ':CALC1:CORR:OFFS:PHAS?', 
                           set_cmd = ':CALC1:CORR:OFFS:PHAS {}', 
                           get_parser = float, 
                           vals = vals.Numbers())
        self.add_parameter('electrical_delay', 
                           get_cmd = 'CALC1:CORR:EDEL:TIME?', 
                           set_cmd = 'CALC1:CORR:EDEL:TIME {}', 
                           unit = 's',
                           get_parser = float,
                           vals = vals.Numbers()
                           )
        self.add_parameter('trigger_source', 
                            get_cmd = 'TRIG:SOUR?', 
                            set_cmd = 'TRIG:SOUR {}', 
                            vals = vals.Enum('INT', 'EXT', 'MAN', 'BUS')
                            )
        self.add_parameter('trform', 
                            get_cmd = ':CALC1:FORM?', 
                            set_cmd = ':CALC1:FORM {}', 
                            vals = vals.Enum('PLOG', 'MLOG', 'PHAS', 
                                             'GDEL', 'SLIN', 'SLOG', 
                                             'SCOM', 'SMIT', 'SADM', 
                                             'PLIN', 'POL', 'MLIN', 
                                             'SWR', 'REAL', 'IMAG', 
                                             'UPH', 'PPH')
                            )
                        

        self.add_parameter('math', 
                           get_cmd = ':CALC1:MATH:FUNC?', 
                           set_cmd = ':CALC1:MATH:FUNC {}', 
                           vals = vals.Enum('ADD', 'SUBT', 'DIV', 'MULT', 'NORM')
                           )
        self.add_parameter('sweep_type',
                           get_cmd = ':SENS1:SWE:TYPE?', 
                           set_cmd = ':SENS1:SWE:TYPE {}', 
                           vals = vals.Enum('LIN', 'LOG', 'SEGM', 'POW')
                           )
        self.add_parameter('correction', 
                           get_cmd = ':SENS1:CORR:STAT?', 
                           set_cmd = ':SENS1:CORR:STAT {}', 
                           get_parser = int)
        self.add_parameter('smoothing', 
                           get_cmd = ':CALC1:SMO:STAT?', 
                           set_cmd = ':CALC1:SMO:STAT {}', 
                           get_parser = float 
                           )
        self.add_parameter('trace', 
                           set_cmd = None, 
                           get_cmd = self.gettrace)
        self.add_parameter('SweepData', 
                           set_cmd = None, 
                           get_cmd = self.getSweepData)
        self.add_parameter('pdata', 
                           set_cmd = None, 
                           get_cmd = self.getpdata)
        self.add_parameter('sweep_time', 
                           get_cmd = ':SENS1:SWE:TIME?', 
                           set_cmd = None, #generally just adjust ifbw and number of pts to change it,
                           get_parser = float,
                           unit = 's'
                           )
        self.connect_message()
    def gettrace(self):
        '''
        Gets amp/phase stimulus data, returns 2 arrays
        
        Input:
            None
        Output:
            [[mags (dB)], [phases (rad)]]
        '''
        strdata= str(self.ask(':CALC:DATA:FDATA?'))
        data= np.array(list(map(float,strdata.split(','))))
        data=data.reshape((int(np.size(data)/2)),2)
        return data.transpose()
    
    def getSweepData(self):
        '''
        Gets stimulus data in displayed range of active measurement, returns array
        Will return different data depending on sweep type. 
        
        For example: 
            power sweep: 1xN array of powers in dBm
            frequency sweep: 1xN array of freqs in Hz
        Input:
            None
        Output:
            sweep_values (Hz, dBm, etc...)
        '''
        logging.info(__name__ + ' : get stim data')
        strdata= str(self.ask(':SENS1:X:VAL?'))
        return np.array(list(map(float,strdata.split(','))))

            
        