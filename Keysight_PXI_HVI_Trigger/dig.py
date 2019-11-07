import pyhvi
from sys import path
path.append(r'C:\Program Files (x86)\Keysight\SD1\Libraries\Python')
import keysightSD1

class DIG:

    def __init__(self, hvi, digModule, index):
        ''' creates necessary interfaces for digitizer
        '''
        self.digModule = digModule
        self.index = index
        digHviEngineID = digModule.hvi.engines.master_engine
        hvi.engines.add(digHviEngineID, "DIGengine"+str(index))
        self.digEngine = hvi.engines[index]

    def close(self):
        ALL_CHANNELS_MASK = 0xF
        self.digModule.DAQstopMultiple(ALL_CHANNELS_MASK)
        is_open = self.digModule.close()
        return str(is_open)

    def trigger_all(self, hvi):
        moduleActions = self.digModule.hvi.actions
        self.digEngine.actions.add(moduleActions.daq1_trigger, "dig_trigger1")
        self.digEngine.actions.add(moduleActions.daq2_trigger, "dig_trigger2")
        self.digEngine.actions.add(moduleActions.daq3_trigger, "dig_trigger3")
        self.digEngine.actions.add(moduleActions.daq4_trigger, "dig_trigger4")

        daqTrigger1234 = [self.digEngine.actions["dig_trigger1"], self.digEngine.actions["dig_trigger2"],
                            self.digEngine.actions["dig_trigger3"], self.digEngine.actions["dig_trigger4"]]
        instruction = self.digEngine.main_sequence.programming.add_instruction("DAQ trigger", 10, hvi.instructions.action_execute.id)
        instruction.set_parameter(hvi.instructions.action_execute.action, daqTrigger1234)

    def start_all(self):
        self.digModule.DAQstart(1)
        self.digModule.DAQstart(2)
        self.digModule.DAQstart(3)
        self.digModule.DAQstart(4)
