import pyhvi

class AWG:
    ''' wrapper class for keysight AWG interactions 
    '''

    def __init__(self, hvi, awgModule, index):
        ''' creates necessary interfaces for AWG
        '''
        self.awgModule = awgModule
        self.index = index
        awgHviEngineID = awgModule.hvi.engines.master_engine
        hvi.engines.add(awgHviEngineID, "AWGengine"+str(index))
        self.awgEngine = hvi.engines[index]

    def trigger_all(self, hvi):
        ''' adds sequencer instruction to trigger all channels of AWG
        '''
        moduleActions = self.awgModule.hvi.actions

        '''awgEngineSequencer = lambda trigger: self.awgEngine.actions.add(trigger[0], trigger[1])
    
        map(awgEngineSequencer, [
            (moduleActions.awg1_trigger, "awg_trigger1"),
            (moduleActions.awg2_trigger, "awg_trigger2"),
            (moduleActions.awg3_trigger, "awg_trigger3"),
            (moduleActions.awg4_trigger, "awg_trigger4")])'''
        self.awgEngine.actions.add(moduleActions.awg1_trigger, "awg_trigger1")
        self.awgEngine.actions.add(moduleActions.awg2_trigger, "awg_trigger2")
        self.awgEngine.actions.add(moduleActions.awg3_trigger, "awg_trigger3")
        self.awgEngine.actions.add(moduleActions.awg4_trigger, "awg_trigger4")
        
        allTriggers = [self.awgEngine.actions["awg_trigger1"], self.awgEngine.actions["awg_trigger2"],
                     self.awgEngine.actions["awg_trigger3"], self.awgEngine.actions["awg_trigger3"]]
        instruction = self.awgEngine.main_sequence.programming.add_instruction("AWG trigger", 200, hvi.instructions.action_execute.id)
        instruction.set_parameter(hvi.instructions.action_execute.action, allTriggers)

    def return_sequence_name(self):
        return self.awgEngine.main_sequence.name

    def add_register(self, name, init_val):
        ''' add register with name "name" and value "init_value" to instruction sequence
        '''
        reg = self.awgEngine.main_sequence.registers.add(name, pyhvi.RegisterSize.SHORT)
        reg.set_initial_value(init_val)

    def return_register(self, name):
        return self.awgEngine.main_sequence.registers[name]

    def assign_register_value(self, hvi, instr_name, reg_name, value):
        ''' create instruction named "instr_name" to instruction sequence
        which assigns value to reg_name
        '''
        assign_instr = self.awgEngine.main_sequence.programming.add_instruction(instr_name, 100, hvi.instructions.assign.id)
        assign_instr.set_parameter(hvi.instructions.assign.source, value)
        register = self.awgEngine.main_sequence.registers[reg_name]
        assign_instr.set_parameter(hvi.instructions.assign.destination_register, register)

    def increment_register_value(self, hvi, instr_name, reg_name, value=1):
        ''' create instruction named "instr_name" to instruction sequence
        which increments the value of reg_name by value (1 by default)
        '''
        increment_instr = self.awgEngine.main_sequence.programming.add_instruction(instr_name, 100, hvi.instructions.add.id)
        increment_instr .set_parameter(hvi.instructions.add.left_operand, value)
        register = self.awgEngine.main_sequence.registers[reg_name]
        increment_instr.set_parameter(hvi.instructions.add.right_operand, register)
        increment_instr.set_parameter(hvi.instructions.add.result_register, register)

    def read_register(self, name):
        ''' returns value of register with "name"
        '''
        return self.awgEngine.main_sequence.registers[name].read()

    def add_wait(self, name, reg_name):
        ''' adds wait block with "name" to instruction sequence
        length of time determined by value of "reg_name"s
        '''
        waitTime = self.awgEngine.main_sequence.programming.add_wait_time(name, 100)
        waitTime.time = self.awgEngine.main_sequence.registers[reg_name]
