# -*- coding: utf-8 -*-
"""
A driver to control the Keysight VNA P9374A using pyVISA and qcodes

@author: Hatlab: Ryan Kaufman

"""

# import visa
import types
import logging
import numpy as np
import time
from qcodes import (Instrument, VisaInstrument,
                    ManualParameter, MultiParameter,
                    validators as vals)

class Keysight_P9374A(VisaInstrument):
    '''
    This is the driver for the Keysight_P9374A Vector Netowrk Analyzer
    Performs basic manipulations of parameters and data acquisition
    
    Note: this version does not include a way of averaging via a BUS trigger

    '''
    
    def __init__(self, name, address = None, **kwargs):

        '''
        Initializes the Keysight_P9374A, and communicates with the wrapper.

        Input:
          name (string)    : name of the instrument
          address (string) : GPIB address
          reset (bool)     : resets to default values, default=False
        '''
        if address == None: 
            raise Exception('TCP IP address needed')
        logging.info(__name__ + ' : Initializing instrument Keysight PNA')
        
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
        #TODO: Set trg sources
        self.add_parameter('trigger_source', 
                            get_cmd = 'TRIG:SOUR?', 
                            set_cmd = 'TRIG:SOUR {}', 
                            vals = vals.Enum('INT', 'EXT', 'MAN', 'BUS')
                            )
        self.add_parameter('trform', 
                            get_cmd = ':CALC1:FORM?', 
                            set_cmd = ':CALC1:FORM {}', 
                            vals = vals.Enum('MLOG', 'PHAS', 
                                             'GDEL',  
                                             'SCOM', 'SMIT', 'SADM', 
                                             'POL', 'MLIN', 
                                             'SWR', 'REAL', 'IMAG', 
                                             'UPH', 'PPH',  'SLIN', 'SLOG',)
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
        self.add_parameter('sweep_time', 
                           get_cmd = ':SENS1:SWE:TIME?', 
                           set_cmd = None, #generally just adjust ifbw and number of pts to change it,
                           get_parser = float,
                           unit = 's'
                           )
        self.write('CALC1:PAR:MNUM 1') #sets the active msmt to the first channel/trace
        self.connect_message()
        

    
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

    
    def gettrace(self):
        '''
        Gets amp/phase stimulus data, returns 2 arrays
        
        Input:
            None
        Output:
            mags (dB) phases (rad)
        '''
        logging.info(__name__ + ' : get amp, phase stim data')
        prev_trform = self.trform()
        self.trform('POL')
        strdata= str(self.ask(':CALC1:DATA? FDATA'))
        self.trform(prev_trform)
        data= np.array(strdata.split(',')).astype(float)
        
        if len(data)%2 == 0:
            print('reshaping data')
            data=data.reshape(int(len(data)/2),2)
            real=data[:, 0]
            imag=data[:, 1]
            mag=20*np.log10(np.sqrt(real**2+imag**2))
            phs=np.arctan2(imag,real)
            magAndPhase = np.zeros((2, len(real)))
            magAndPhase[0]=mag
            magAndPhase[1]=phs
            return magAndPhase
        else:
            return data#.transpose() # mags, phase
        

    def data_to_mem(self):        
        '''
        Calls for data to be stored in memory
        '''
        logging.debug(__name__+": data to mem called")
        self.write(":CALC1:MATH:MEM")


