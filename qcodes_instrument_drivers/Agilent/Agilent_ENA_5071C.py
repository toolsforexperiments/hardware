
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
                            # '''
                            # Set trace format. MLOGarithmic|PHASe|GDELay| SLINear|
                            # SLOGarithmic|SCOMplex|SMITh|SADMittance|PLINear|PLOGarithmic|
                            # POLar|MLINear|SWR|REAL| IMAGinary|UPHase|PPHase
                            # '''
                            
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
        self.add_parameter('fdata', 
                           set_cmd = None, 
                           get_cmd = self.getfdata)
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
        
        
####################### Custom Functions 
    def average_restart(self):
        self.write('SENS1:AVER:CLE')  
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
        
    def getfdata(self):
        '''
        Gets freq stimulus data, returns array
        
        Input:
            None
        Output:
            freqvalues array (Hz)
        '''
        logging.info(__name__ + ' : get f stim data')
        strdata= str(self.ask(':SENS1:FREQ:DATA?'))
        return np.array(list(map(float,strdata.split(','))))
    def getpdata(self):
        '''
        Get the probe power sweep range
        
        Input: 
            None
        Output:
            probe power range (numpy array)
        '''
        logging.debug(__name__ + ' : get the probe power sweep range')
        return np.linspace(self.power_start(), self.power_stop(), 1601)
        
    def set_bundle(self, bundle):
        '''
        This lets you set values for the VNA all at once in a dictionary by using a key
        '''
        for key in bundle:
            try: 
                if type(bundle[key]) == str: 
                    eval("self."+key+"(str('"+bundle[key]+"'))") 
                else:
                    eval("self."+key+"(str("+str(bundle[key])+"))") 
            except AttributeError:
                raise Exception("Key '" + str(key)+"' not a valid VNA setting, check your dictionary for typos compared to VNA settings in driver using VNA.get_all()")

        
    def get_bundle(self,bundle):
        ''' 
        This retrieves the current elements in the bundle dictionary, but JUST the keys that you give it. It also calls BS if you give it a garbage key.
        '''
        for key in bundle:
            try: 
                if type(bundle[key]) == str: 
                    bundle[key] = eval("self."+key+"(str('"+bundle[key]+"'))") 
                else:
                    bundle[key] = eval("self."+key+"(str("+str(bundle[key])+"))") 
            except AttributeError:
                raise Exception("Key '" + str(key)+"' not a valid VNA setting, check your dictionary for typos compared to VNA settings in driver using VNA.get_all()")
                
        return bundle.copy() #the copy is because you want them to be seperate from the original dictionary. If it were C they would have different pointers
      
    def data_to_mem(self):        
        '''
        Calls for data to be stored in memory
        '''
        logging.debug(__name__+": data to mem called")
        self.write(":CALC1:MATH:MEM")
    def average(self, number): 
        #setting averaging timeout, it takes 52.02s for 100 traces to average with 1601 points and 2kHz IFBW, so 
        '''
        Sets the number of averages taken, waits until the averaging is done, then gets the trace
        '''
        assert number > 0
        
        prev_trform = self.trform()
        self.trform('PLOG')
        self.trigger_source('BUS')
        
        buffer_time = 0.5
        if number == 1:
           
            self.averaging(0)
            self.average_trigger(0)
            s_per_trace = self.sweep_time()
            self.timeout(number*s_per_trace+buffer_time)
            self.trigger()
            return self.gettrace()
        else: 
            #wait just a little longer for safety #TODO: find a way to make this better than 8%
            #turn on the average trigger
            
            self.averaging(1)
            self.average_trigger(1)
            self.avgnum(number)
            prev_timeout = self.timeout()
            s_per_trace = self.sweep_time()
            self.timeout(number*s_per_trace+buffer_time)
            print("Waiting {:.3f} seconds for {} averages...".format(self.timeout(), number))
            self.write(':TRIG:SING')
            # print('triggered')
            #the next command will hang the kernel until the averaging is done
            print(self.ask('*OPC?'))
            # print('timeout check')
            return self.gettrace()
    
    def savetrace(self, avgnum = 500, savedir = None): 
        if savedir == None:
            import easygui 
            savedir = easygui.filesavebox("Choose file to save trace information: ")
            assert savedir != None
            
        elif savedir == "previous": 
            savedir = self.previous_save
            assert savedir != None
        fdata = self.getfdata()
        prev_trform = self.trform()
        self.trform('PLOG')
        tracedata = self.average(avgnum)
        self.trform(prev_trform)
        self.trigger_source('INT')
        self.previous_save = savedir
        import h5py
        file = h5py.File(savedir, 'w')
        file.create_dataset("VNA Frequency (Hz)", data = fdata)
        file.create_dataset("S21", data = tracedata)
        file.create_dataset("Phase (deg)", data = tracedata[1])
        file.create_dataset("Power (dB)", data = tracedata[0])
        file.close()
        
        
    def save_important_info(self, savedir = None):
        if savedir == None:
            import easygui 
            savedir = easygui.filesavebox("Choose where to save VNA info: ", default = savedir)
            assert savedir != None
        file = open(savedir+'.txt', 'w')
        file.write(self.name+'\n')
        file.write("Power: "+str(self.power())+'\n')
        file.write("Frequency: "+str(self.fcenter())+'\n')
        file.write("Span: "+str(self.fspan())+'\n')
        file.write("EDel: "+str(self.electrical_delay())+'\n')
        file.write("Num_Pts: "+str(self.num_points())+'\n')
        print("Power: "+str(self.power())+'\n'+"Frequency: "+str(self.fcenter())+'\n'+"Span: "+str(self.fspan())+'\n'+"EDel: "+str(self.electrical_delay())+'\n'+"Num_Pts: "+str(self.num_points())+'\n')
        file.close()
        return savedir
    
    def trigger(self): 
        self.write(':TRIG:SING')
        return None
    def set_to_manual(self): 
        self.rfout(1)
        self.averaging(1)
        self.avgnum(1)
        self.average_trigger(0)
        self.trform('PHAS')
        self.trigger_source('INT')