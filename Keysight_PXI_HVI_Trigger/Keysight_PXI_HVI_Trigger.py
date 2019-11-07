#!/usr/bin/env python
import sys
import os
import numpy as np
from BaseDriver import LabberDriver, Error
sys.path.append('C:\\Program Files (x86)\\Keysight\\SD1\\Libraries\\Python')
import keysightSD1
from triggerloop import TriggerLoop

#TODO change driver name
class Driver(LabberDriver):
    """Keysigh PXI HVI trigger"""

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # timeout
        self.timeout_ms = int(1000 * self.dComCfg['Timeout'])
        # get PXI chassis
        self.chassis = int(self.comCfg.address)
        # auto-scan chassis address
        n_unit = keysightSD1.SD_Module.moduleCount()
        all_chassis = [
            keysightSD1.SD_Module.getChassisByIndex(n) for n in range(n_unit)]
        # check if user-given chassis is available
        if n_unit > 0 and self.chassis not in all_chassis:
            # if all units are in the same chassis, override given PXI chassis
            if np.all(np.array(all_chassis) == all_chassis[0]):
                self.chassis = all_chassis[0]

        # number of slots in chassis
        self.n_slot = 18
        # supported AWGs and Digitizers
        self.AWGS = ['M3201', 'M3202', 'M3300', 'M3302']
        self.DIGS = ['M3100', 'M3102']
        # keep track of current PXI configuration
        # 0: None, 1: AWG, 2: Digitizer
        self.units = [0] * self.n_slot
        self.awg_slots = []
        self.dig_slots = []
        self.old_trig_period = -1.0
        self.old_dig_delay = -1.0

        # defaulting to chassisnumber = 1 because pyhvi cannot handle multiple chassis 
        self.trigger_loop = TriggerLoop(1)

    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        # do not check for error if close was called with an error
        try:
            # close instruments
            self.triggerloop.close()
        except Exception:
            # never return error here
            pass

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # continue depending on quantity
        if quant.name == 'Auto-detect':
            # auto-detect units
            if value:
                self.auto_detect()
        elif quant.name == 'Scan':
            # when scanning, just run auto-detect
            self.auto_detect()
        else:
            # just set the quantity value, config will be set at final call
            quant.setValue(value)

        # only update configuration at final call
        if self.isFinalCall(options):
            self.configure_hvi()

        return value

    def configure_hvi(self):
        """Configure and start/stop HVI depending on UI settings"""
        # get units
        units = self.get_pxi_config_from_ui()
        n_awg = len([x for x in units if x == 1])
        n_dig = len([x for x in units if x == 2])

        # if no units in use, just stop
        if (n_awg + n_dig) == 0:
            return

        # check if unit configuration changed, if so reload HVI
        if units != self.units:
            # stop current HVI, may not even be running
            self.units = units

            # we need at least one AWG
            if n_awg == 0:
                raise Error('This driver requires at least one AWG.')

            # assign units, run twice to ignore errors before all units are set
            awg_slots = []
            dig_slots = []
            for m in range(2):
                for n, unit in enumerate(units):
                    # if unit in use, assign to module
                    if unit == 0:
                        continue
                    elif unit == 1:
                        # AWG
                        awg_slots.append(n+1)
                    elif unit == 2:
                        # digitizer
                        dig_slots.append(n+1)

        # only update trig period or slots if necessary, takes time to re-compile
        if (awg_slots != self.awg_slots or dig_slots != self.dig_slots):
            # hardcoding chassis number = 1 because pyhvi won't work
            # with multiple chassis
            self.awg_slots = awg_slots
            self.dig_slots = dig_slots
            #awgModules = self.open_modules(1, awg_slots, 'awg')
            #digModules = self.open_modules(1, dig_slots, 'dig')
            #close_log, awg_info, dig_info = self.trigger_loop.set_slots(self.awg_slots, self.dig_slots, slot_free)
            
            close_log = self.trigger_loop.close_modules()

            self.log('closed: '+close_log)

            self.trigger_loop.awg_slots = awg_slots
            self.trigger_loop.dig_slots = dig_slots

            awg_info, dig_info = self.trigger_loop.init_hw()

            self.log('awg: '+awg_info[0], awg_info[1])
            self.log('dig: '+dig_info[0], dig_info[1])

            # always check trig period now because we have to recompile anyway
            self.old_trig_period = self.getValue('Trig period')
            self.old_dig_delay = self.getValue('Digitizer delay')

            wait = round(self.getValue('Trig period') / 10E-9) - 46
            digi_wait = round(self.getValue('Digitizer delay') / 10E-9)
            # special case if only one module: add 240 ns extra delay
            if (n_awg + n_dig) == 1:
                wait += 24

            self.trigger_loop.write_instructions(wait*10, digi_wait)
            self.trigger_loop.prepare_hw()

        if (self.getValue('Trig period') != self.old_trig_period or
                self.getValue('Digitizer delay') != self.old_dig_delay):

            self.old_trig_period = self.getValue('Trig period')
            self.old_dig_delay = self.getValue('Digitizer delay')
            # update trig period, include 460 ns delay in HVI
            wait = round(self.getValue('Trig period') / 10E-9) - 46
            digi_wait = round(self.getValue('Digitizer delay') / 10E-9)
            # special case if only one module: add 240 ns extra delay
            if (n_awg + n_dig) == 1:
                wait += 24

            self.trigger_loop.write_instructions(wait, digi_wait)
            self.trigger_loop.prepare_hw()

        # start or stop the HVI, depending on output state
        if self.getValue('Output'):
            self.trigger_loop.run()

        else:
            self.trigger_loop.close()

    def check_keysight_error(self, code):
        """Check and raise error"""
        if code >= 0:
            return
        # get error message
        raise Error(keysightSD1.SD_Error.getErrorMessage(code))

    def open_modules(self, chassis, slots, type):
        ''' 
        slots = list of slot numbers of device
        type = string 'awg' to open awg modules, 'dig' to
        open digitizer modules
        open_modules creates and returns a list keysightSD1 module objects
        '''
        options = "channelNumbering=keysight"
        model = ""
        modules = []
        if slots:
            for slot in slots:
                if type == 'awg':
                    module = keysightSD1.SD_AOU()
                elif type == 'dig':
                    module = keysightSD1.SD_AIN()
                else:
                    raise Error('Only AWGs and digitizers are supported')
                self.log('slot number: '+str(slot))
                # check that we haven't already assigned a module to this slot
                if self.slot_free[slot-1] == True:
                    id_num = module.openWithOptions(model, chassis, slot, options)

                    if id_num < 0:
                        raise Error("Error opening module in chassis {}, slot {}, opened with ID: {}".format(chassis, slot, id_num))
                    if not module.hvi:
                        raise Error("Module in chassis {} and slot {} does not support HVI2.0... exiting".format(awgModule.getChassis(), awgModule.getSlot()))
                    modules.append(module)
                    self.slot_free[slot-1] = False
                    self.log('slots status: '+str(self.slot_free))
                else:
                    self.log('slot taken, check behavior', 30)
        return modules

    def auto_detect(self):
        """Auto-detect units"""
        # start by clearing old config
        for n in range(self.n_slot):
            self.setValue('Slot %d' % (n + 1), 0)

        # loop through all units, make sure chassis match
        n_unit = keysightSD1.SD_Module.moduleCount()
        for n in range(n_unit):
            chassis = keysightSD1.SD_Module.getChassisByIndex(n)
            slot = keysightSD1.SD_Module.getSlotByIndex(n)
            # if chassis match, check unit type
            if chassis == self.chassis:
                model = keysightSD1.SD_Module.getProductNameByIndex(n)
                if model[:5] in self.AWGS:
                    self.setValue('Slot %d' % slot, 'AWG')
                elif model[:5] in self.DIGS:
                    self.setValue('Slot %d' % slot, 'Digitizer')

    def get_pxi_config_from_ui(self):
        """Get PXI config from user interface"""
        units = []
        for n in range(self.n_slot):
            units.append(self.getValueIndex('Slot %d' % (n + 1)))
        return units


if __name__ == '__main__':
    pass
