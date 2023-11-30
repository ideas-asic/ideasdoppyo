
import operator
from copy import deepcopy
import csv

class Register(object):
    def __init__(self, addr, name, value=0, reset=0, bitmask=0xff, fieldpos_list=None, fieldval_list=None, size=0):
        self.addr = addr
        self.name = name
        self.reset = reset
        self.bitmask = bitmask
        self.fieldpos_list = [0] * 8
        self.fieldval_list = [0] * 8
        self.size = size 
        self.value = value
    
    
    def set_value(self, value):
        ''' Sets the register value. Operates on the Memory Map. '''
        # The majority of the code is for aligning the MemoryMap style to the existing Testbench register write / read functionaloty.
        
        if len('{:0b}'.format(value)) <= (self.size+1): 
            self.value = value 
        else:
            self.value = int('{:08b}'.format(value)[(7-self.size):],2)
        
        bin_val_list = [c for c in '{:08b}'.format(value)]
        bitfield_lengths = []
        bitfield_length=0
        
        # Populate the bitfield lengths of the register
        for k in reversed(range(len(self.fieldpos_list))):
            if self.fieldpos_list[k] == 1 and self.fieldpos_list[k-1] == 1:
                bitfield_lengths.append(bitfield_length+1)   # NOTE - '+1' not in tb_products
                bitfield_length=0
            elif self.fieldpos_list[k] == 0 and self.fieldpos_list[k-1] == 1:
                bitfield_length = bitfield_length + 1
                bitfield_lengths.append(bitfield_length)
                bitfield_length=0
            elif (self.fieldpos_list[k] == 1 and self.fieldpos_list[k-1] == 0) or (self.fieldpos_list[k] == 0 and self.fieldpos_list[k-1]) == 0:
                if sum(bitfield_lengths)<self.size: 
                    bitfield_length = bitfield_length + 1
        
        length_index = 0
       
        # Populate fieldval_list with register value
        for k in reversed(range(len(self.fieldpos_list))):
            if self.fieldpos_list[k] == 1:
                binval=''.join(bin_val_list[k-bitfield_lengths[length_index]+1:k+1])
                length_index = length_index + 1
                self.fieldval_list[k] = int(str(binval),2)

    def write_reg(self, value=None, hook=None):
        ''' 
        Write a register value. Operates on the Memory Map and ASIC. 
        If value is passed, uses passed register value, otherwise uses 
        the existing register value
        '''
        if value is None:
            hook(self.addr, self.value, self.fieldpos_list, self.fieldval_list)
        else:
            self.set_value( value )
            hook(self.addr, self.value, self.fieldpos_list, self.fieldval_list)
    
    def read_reg(self, hook=None):
        ''' Read a register value. Operates on the Memory Map and ASIC. '''
        read_data =  hook(self.addr, self.fieldpos_list)
        self.set_value( read_data )
        return read_data
    
    
    def __repr__(self):
        return("Addr: "+str(self.addr)+ " Name: "+str(self.name)+" Value: "+str(self.value)+" fieldpos: "+str(bin(int(''.join(map(str, self.fieldpos_list)), 2)))+"\n")
        
class MemoryField(object):
    def __init__(self, name="",addr=None, map=None, fields=[{'reset': 0, 'bitmask': 0, 'romask': 0, 'wrxmask': 0, 'addr': 0, 'endbit': 0, 'pumask': 0, 'rrmask': 0, 'logical': 1, 'startbit': 0}]):
        self.name = name
        self.fields = fields
        self.addr = fields[0]['addr']
        self.map = map
#        if map:
#            self.set_value(value)
#            print('map set, fields', fields, self.get_value())
#            print('map ', self.map)
            
    def make_bitmask(self, startbit, endbit):
        bitmaskA = (1 << (endbit + 1))-1      
        bitmaskB = (1 << (startbit))-1
        bitmask = bitmaskA - bitmaskB
        return(bitmask)

    
    def make_field_tuple(self, addr=None, startbit=None, endbit=None, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0, logical=0):
        if not (addr>=0):
            raise SyntaxError
        if not (startbit>=0):
            raise SyntaxError
        if not (endbit>=0):
            raise SyntaxError            
        
        return( {
            'addr'    : addr, 
            'startbit': startbit, 
            'endbit'  : endbit, 
            'bitmask' : self.make_bitmask(startbit, endbit),
            'romask'  : romask, 
            'reset'   : reset, 
            'pumask'  : pumask,
            'rrmask'  : rrmask,
            'wrxmask' : wrxmask,
            'logical' : logical,
            }
            ) 
        
    def get_value(self, map=None):
        """ get value based on memory map register values and field lookup tuples """
        if not map:
            map = self.map
        x = 0
        bits = 0
        for f in self.fields:
            f0 = (map.registers[f['addr']].value & f['bitmask']) >> f['startbit']
            x = x | (f0 << bits)
            bits = bits - f['startbit'] + f['endbit'] + 1
        return(x)
    
    def set_value(self, value, map=None):
        """ set value spread over memory map register values based on 'field' lookup tuples """
        if not map:
            map = self.map        
        #print("Hallo %d" % value , map.registers)
        for f in self.fields:
            reg = map.registers[f['addr']]
            
            # Identify field positions and field values for a register            
            if f['logical'] !=1:
                reg.fieldpos_list[7-f['startbit']]=1
                reg.fieldval_list[7-f['startbit']]=value            
             
                
#            print("xx", reg.bitmask, f['bitmask'], value, f['startbit'])
#            print("xx", (value & (f['bitmask'] >> f['startbit'])))
            
            # Set register value 
            reg.value = ((reg.value & (reg.bitmask - f['bitmask'])) | 
                        (value & (f['bitmask'] >> f['startbit'])) << f['startbit'] )
            value >>= (f['endbit'] - f['startbit'] + 1)
            
            
            if reg.size < f['endbit']:
                reg.size = f['endbit']
            
            if f['logical'] ==1:
                reg.fieldpos_list[7]=1
                reg.fieldval_list[7]=reg.value
            
    def write_value(self, value, hook=None, map=None):
        """ set_value + write to associated register on ASIC. Does not work on logical fields"""
        if not map:
            map = self.map
        self.set_value(value)
        map.registers[self.addr].write_reg(hook=hook)

    def read_value(self, hook=None, map=None):
        """ Read from associated register on ASIC + get_value. Does not work on logical fields"""
        if not map:
            map = self.map
        map.registers[self.addr].read_reg(hook=hook)
        return self.get_value()
            
    def __repr__(self):
        return("%s 0x%04X" % (self.name, self.get_value()))

class MemoryMap(object):
    
    def __init__(self):
        self.registers  = {}
        self._regnames  = {}
        self.fields     = {}
        
    def add_field(self, field, value=0):
        field.map = self
        self.fields[field.name] = field
        field.set_value(value)
        
    def add_register(self, addr, name, reset, bitmask=0xff):
        self.registers[addr] = Register(addr, name, reset, bitmask)
    
    def register(self, name):
        ''' Not used for the moment. _regnames not implemented. '''
        return(self.registers[self._regnames[name]])
        
    def update_maps(self):
        for i in self.fields.values():
            i.map = self
        for i in self.registers.values():
            i.map = self
      
    def foreach_newreg(self, old_map=None, hook=None):
        for regaddr, reg in old_map.registers.items():
            
            if (reg.value != self.registers[regaddr].value):
                # print("Writing addr:" + str(regaddr) + str(self.registers[regaddr].value))
                #hook(regaddr, self.registers[regaddr], self.registers[regaddr].value)
                hook(regaddr, self.registers[regaddr].value, self.registers[regaddr].fieldpos_list, self.registers[regaddr].fieldval_list)                
                # [TODO] Reset pulse registers.
    
    
    def init_ram(self, old_map=None, hook=None):
        '''
        Not implemented
        
        Initializes all RAM addresses with values zero.
        '''
 
        for regaddr, reg in old_map.registers.items():
    
            if regaddr in list(range(8192,12290,2)):
            
                hook( regaddr, 0, self.registers[ regaddr ].fieldpos_list, self.registers[ regaddr ].fieldval_list )
        
    
    def checkerboard_alladdr(self, old_map=None, hook=None):
        ''' Writes checkerboard pattern to all addresses '''
        
        for regaddr, reg in old_map.registers.items():
            
            hook( regaddr, 0x55, self.registers[ regaddr].fieldpos_list, self.registers[ regaddr ].fieldval_list )
            
            
    
        
    def copy(self):
        x = deepcopy(self)
        x.update_maps()
        return(x)
    
    def compare_map(self, other_map=None):
        ''' Compares bitfields of two MemoryMaps '''
        compare_ok = True
        sorted_tuples = (sorted(self.fields.values(), key=operator.attrgetter('addr'))) # Sort tuples after 'addr'
        for f in sorted_tuples:
            if f.fields[0]['addr'] == 0:
                continue # IRQ_ENABLE address used for some Testbenchs stuff
            elif f.fields[0]['addr'] == 0xFC00:
                continue # SPI_RESET not a register                
            elif f.fields[0]['romask'] == 1:
                continue # Skip ReadOnly
            elif f.fields[0]['rrmask'] == 1:
                continue # Skip ReadReset   
            elif f.fields[0]['pumask'] == 1:
                continue # Skip PulseReg
            elif f.fields[0]['wrxmask'] == 1:
                continue # Skip write/read/ext since write only manifests after sequencer sync reset
            elif f.fields[0]['logical'] == 1:
                continue # Skip logical bitfields
            elif 'no_reg' in f.name:
                continue # Skip 'no_reg' empty bitfields (not actual registers)                  
            else:
                if f.get_value() != other_map.fields[f.name].get_value():
                    print('** Error ** Address: ' + str(f.addr) + ' ' + str(f) + ' (self) != ' + str(other_map.fields[f.name]))
                    compare_ok = False
        
        return compare_ok
    
    def compare_map_bitflip(self, other_map=None):
        ''' Calculates bitflips between two MemoryMaps, e.g. write vs. read maps '''
        bitflips_allreg = 0              # Initial value
        bitflips_list = []
        bitflips_returnstring = "Total number of bitflips measured: "
        compare_ok = True
        sorted_tuples = (sorted(self.fields.values(), key=operator.attrgetter('addr'))) # Sort tuples after 'addr'
        for f in sorted_tuples:
            if f.fields[0]['addr'] == 0:
                continue # IRQ_ENABLE address used for some Testbenchs stuff
            elif f.fields[0]['addr'] == 0xFC00:
                continue # SPI_RESET not a register
            elif f.fields[0]['addr'] == 0x3000:
                continue # Not a real register                 
            elif f.fields[0]['romask'] == 1:
                continue # Skip ReadOnly
            elif f.fields[0]['rrmask'] == 1:
                continue # Skip ReadReset   
            elif f.fields[0]['pumask'] == 1:
                continue # Skip PulseReg
            elif f.fields[0]['wrxmask'] == 1:
                continue # Skip write/read/ext since write only manifests after sequencer sync reset
            elif f.fields[0]['logical'] == 1:
                continue # Skip logical bitfields
            elif 'no_reg' in f.name:
                continue # Skip 'no_reg' empty bitfields (not actual registers)                  
            else:
                new_val = f.get_value()
                old_val = other_map.fields[f.name].get_value()
                diff_val = "{0:b}".format(new_val^old_val)
                if new_val != old_val:
                    bitflips = sum(int(d) for d in diff_val)
                    bitflips_allreg += bitflips
                    bitflips_list.append((f.addr, bitflips))
                    print('You have read ' + str(new_val) + ' when you wrote ' + str(old_val))
                    print('** BITFLIP ** Address: ' + str(f.addr) + ' ' + str(f) + ' # of Bitflips = ' + str(bitflips))
                    compare_ok = False
                    
        return bitflips_returnstring + str(bitflips_allreg), bitflips_list, compare_ok
    
    def compare_reg(self, addr, other_map=None):
        ''' Compares the value of two registers '''
        compare_ok = True
        self_value  = self.registers[addr].value
        other_value = other_map.registers[addr].value
        if self_value != other_value :
            print('** Error ** Address: ' + str(addr) + ' Data (self): ' + str(self_value) + ' != ' + str(other_value))
            compare_ok = False
        
        return compare_ok
    
    def dump_mem_diff(self, event, filename='conf_diff_dump.txt', other_map=None ):
        ''' Compares bitfields of two MemoryMaps and dumps to file'''
        write_string = 'Config differences in two MemoryMaps (this_map, other_map) \n'
        write_string += 'Event: "' + str(event) + '" \n'
        sorted_tuples = (sorted(self.fields.values(), key=operator.attrgetter('addr'))) # Sort tuples after 'addr'
        for f in sorted_tuples:
            if f.get_value() != other_map.fields[f.name].get_value():
                write_string+=str(self.fields[f.name]) + "," + str(other_map.fields[f.name]) + '\n'

        with open(filename, 'w') as file:
            file.write( write_string )
        
        
    # def write_read_test(self):
    # ''' Writes and reads from all addresses and checks the data.'''
    

        


class ADC(object):
    
    def __init__(self, number, map=None):
        self.number = number
        self.map = map
        self.coeffs = [0]*14                                                    # Encoded as read from ASIC (data currently in ASIC)
        self.coeffs_decoded = [0]*14                                            # Decoded based on self.coeffs
        self.coeffs_decoded_scaled = [0]*14                                     # Scaled self.coeffs_decoded
        self.coeffs_encoded = [0]*14                                            # Encoded after rescaling
        self.coeffs_encoded_length = [4,5,6,7,8,9,10,11,12,13,14,15,16,17]      # Encoded coefficient length list
        self.coeffs_decoded_per_stage = [0]*6                                   # Select decoded coefficients per stage

    def start_calibration(self, hook=None):
        ''' 
        Starts calibration.
        Operates on memory map, sets pulse reg and resets pulse reg in func.        
        '''
        regaddr = self.map.fields['adc_cal_start_calibration'].fields[0]['addr']
        reg = self.map.registers[regaddr]
        
        self.map.fields['adc_cal_start_calibration'].set_value(1)
        hook(regaddr, reg.value, reg.fieldpos_list, reg.fieldval_list)                 
        self.map.fields['adc_cal_start_calibration'].set_value(0)
        
    def reset_calibration_fsm(self, hook=None):
        ''' 
        Resets calibration FSM.
        Operates on memory map, sets pulse reg and resets pulse reg in func. 
        '''
        regaddr = self.map.fields['adc_cal_syncreset_fsm'].fields[0]['addr']
        reg = self.map.registers[regaddr]
        
        self.map.fields['adc_cal_syncreset_fsm'].set_value(1)
        hook(regaddr, reg.value, reg.fieldpos_list, reg.fieldval_list)                 
        self.map.fields['adc_cal_syncreset_fsm'].set_value(0)                 

    def set_pa_gain(self, gain):
        ''' 
        Sets the PA gain of all VADCs 0-15 or AADC.        
        Operates on mamory map.
        '''                
        pass

    def get_pa_gain(self):
        ''' 
        Gets the PA gain of all VADCs 0-15 or AADC.
        Operates on mamory map.        
        '''                
        pass

    def read_coeffs(self, hook=None):
        ''' 
        Reads coefficients from the ASIC and updates the memory map. 
        Stores coefficients also in local variables for further processing.               
        '''    
        # Read coeffs
        adc_coeff_mem_addresses         = list(range(1024+0+32*self.number,1024+19+32*self.number))
        
        for addr in adc_coeff_mem_addresses:
            read_data1 = self.map.registers[ addr ].read_reg( hook = hook ) # AHA: Not sure why, but 2x read ops are needed to get data out. Should be investigated.
            read_data1 = self.map.registers[ addr ].read_reg( hook = hook )       

        self.coeffs[0] = self.map.fields['vadc%d_submul'%self.number].get_value()
        self.coeffs[1] = self.map.fields['vadc%d_st6_c1'%self.number].get_value()
        self.coeffs[2] = self.map.fields['vadc%d_st6_c2'%self.number].get_value()
        self.coeffs[3] = self.map.fields['vadc%d_st5_c1'%self.number].get_value()
        self.coeffs[4] = self.map.fields['vadc%d_st5_c2'%self.number].get_value()
        self.coeffs[5] = self.map.fields['vadc%d_st4_c1'%self.number].get_value()
        self.coeffs[6] = self.map.fields['vadc%d_st4_c2'%self.number].get_value()
        self.coeffs[7] = self.map.fields['vadc%d_st3_c1'%self.number].get_value()
        self.coeffs[8] = self.map.fields['vadc%d_st3_c2'%self.number].get_value()
        self.coeffs[9] = self.map.fields['vadc%d_st2_c1'%self.number].get_value()
        self.coeffs[10] = self.map.fields['vadc%d_st2_c2'%self.number].get_value()
        self.coeffs[11] = self.map.fields['vadc%d_st1_c1'%self.number].get_value()
        self.coeffs[12] = self.map.fields['vadc%d_st1_c2'%self.number].get_value()
        self.coeffs[13] = self.map.fields['vadc%d_st1_c3'%self.number].get_value()

        # Prints can be deleted after debug phase        
        #print('coeff(READ) vadc%d_submul'%self.number + ": " + str( self.coeffs[0] ))
        #print('coeff(READ) vadc%d_st6_c1'%self.number + ": " + str( self.coeffs[1] ))
        #print('coeff(READ) vadc%d_st6_c2'%self.number + ": " + str( self.coeffs[2] ))
        #print('coeff(READ) vadc%d_st5_c1'%self.number + ": " + str( self.coeffs[3] ))
        #print('coeff(READ) vadc%d_st5_c2'%self.number + ": " + str( self.coeffs[4] ))
        #print('coeff(READ) vadc%d_st4_c1'%self.number + ": " + str( self.coeffs[5] ))
        #print('coeff(READ) vadc%d_st4_c2'%self.number + ": " + str( self.coeffs[6] ))
        #print('coeff(READ) vadc%d_st3_c1'%self.number + ": " + str( self.coeffs[7] ))
        #print('coeff(READ) vadc%d_st3_c2'%self.number + ": " + str( self.coeffs[8] ))
        #print('coeff(READ) vadc%d_st2_c1'%self.number + ": " + str( self.coeffs[9] ))
        #print('coeff(READ) vadc%d_st2_c2'%self.number + ": " + str( self.coeffs[10] ))
        #print('coeff(READ) vadc%d_st1_c1'%self.number + ": " + str( self.coeffs[11] ))
        #print('coeff(READ) vadc%d_st1_c2'%self.number + ": " + str( self.coeffs[12] ))
        #print('coeff(READ) vadc%d_st1_c3'%self.number + ": " + str( self.coeffs[13] ))

    def write_coeffs(self, coeffs, hook = None):
        ''' 
        Updates the memory map and writes to ASIC.        
        Operates on memory map and ASIC.        
        '''                
        
        # Update memory map
        self.map.fields['vadc%d_submul'%self.number].set_value(coeffs[0])
        self.map.fields['vadc%d_st6_c1'%self.number].set_value(coeffs[1])
        self.map.fields['vadc%d_st6_c2'%self.number].set_value(coeffs[2])
        self.map.fields['vadc%d_st5_c1'%self.number].set_value(coeffs[3])
        self.map.fields['vadc%d_st5_c2'%self.number].set_value(coeffs[4])
        self.map.fields['vadc%d_st4_c1'%self.number].set_value(coeffs[5])
        self.map.fields['vadc%d_st4_c2'%self.number].set_value(coeffs[6])
        self.map.fields['vadc%d_st3_c1'%self.number].set_value(coeffs[7])
        self.map.fields['vadc%d_st3_c2'%self.number].set_value(coeffs[8])
        self.map.fields['vadc%d_st2_c1'%self.number].set_value(coeffs[9])
        self.map.fields['vadc%d_st2_c2'%self.number].set_value(coeffs[10])
        self.map.fields['vadc%d_st1_c1'%self.number].set_value(coeffs[11])
        self.map.fields['vadc%d_st1_c2'%self.number].set_value(coeffs[12])
        self.map.fields['vadc%d_st1_c3'%self.number].set_value(coeffs[13])
        
        # Update self.coeffs with data written to ASIC.
        self.coeffs = coeffs
        
        # Write
        adc_coeff_mem_addresses         = list(range(1024+0+32*self.number,1024+19+32*self.number))
        
        for addr in adc_coeff_mem_addresses:
            self.map.registers[ addr ].write_reg( hook = hook )
            
        
    def decode_coeffs(self):
        ''' 
        Decodes the ADC coefficients.        
        Operates on local variables.        
        '''        
        # Decode
        for i in range(len(self.coeffs)):
            if ('{:b}'.format(self.coeffs[i]).zfill(self.coeffs_encoded_length[i])[0] == '1'): # check if MSB = 1
                self.coeffs_decoded[i] = int( '100'+'{:b}'.format(self.coeffs[i]).zfill(self.coeffs_encoded_length[i])[1:self.coeffs_encoded_length[i]] , 2)
            elif ('{:b}'.format(self.coeffs[i]).zfill(self.coeffs_encoded_length[i])[0] == '0'): # check if MSB = 0
                self.coeffs_decoded[i] = int( '11'+'{:b}'.format(self.coeffs[i]).zfill(self.coeffs_encoded_length[i])[1:self.coeffs_encoded_length[i]] , 2)                

        self.coeffs_decoded_per_stage[0] = [self.coeffs_decoded[11], self.coeffs_decoded[12], self.coeffs_decoded[13]]   
        self.coeffs_decoded_per_stage[1] = [self.coeffs_decoded[9], self.coeffs_decoded[10]]   
        self.coeffs_decoded_per_stage[2] = [self.coeffs_decoded[7], self.coeffs_decoded[8]]     
        self.coeffs_decoded_per_stage[3] = [self.coeffs_decoded[5], self.coeffs_decoded[6]]     
        self.coeffs_decoded_per_stage[4] = [self.coeffs_decoded[3], self.coeffs_decoded[4]]     
        self.coeffs_decoded_per_stage[5] = [self.coeffs_decoded[1], self.coeffs_decoded[2]]     

        
        # Prints can be deleted after debug phase
        #print('coeff(DECODED) vadc%d_submul'%self.number + ": " + str( self.coeffs_decoded[0] ))
        #print('coeff(DECODED) vadc%d_st6_c1'%self.number + ": " + str( self.coeffs_decoded[1] ))
        #print('coeff(DECODED) vadc%d_st6_c2'%self.number + ": " + str( self.coeffs_decoded[2] ))
        #print('coeff(DECODED) vadc%d_st5_c1'%self.number + ": " + str( self.coeffs_decoded[3] ))
        #print('coeff(DECODED) vadc%d_st5_c2'%self.number + ": " + str( self.coeffs_decoded[4] ))
        #print('coeff(DECODED) vadc%d_st4_c1'%self.number + ": " + str( self.coeffs_decoded[5] ))
        #print('coeff(DECODED) vadc%d_st4_c2'%self.number + ": " + str( self.coeffs_decoded[6] ))
        #print('coeff(DECODED) vadc%d_st3_c1'%self.number + ": " + str( self.coeffs_decoded[7] ))
        #print('coeff(DECODED) vadc%d_st3_c2'%self.number + ": " + str( self.coeffs_decoded[8] ))
        #print('coeff(DECODED) vadc%d_st2_c1'%self.number + ": " + str( self.coeffs_decoded[9] ))
        #print('coeff(DECODED) vadc%d_st2_c2'%self.number + ": " + str( self.coeffs_decoded[10] ))
        #print('coeff(DECODED) vadc%d_st1_c1'%self.number + ": " + str( self.coeffs_decoded[11] ))
        #print('coeff(DECODED) vadc%d_st1_c2'%self.number + ": " + str( self.coeffs_decoded[12] ))
        #print('coeff(DECODED) vadc%d_st1_c3'%self.number + ": " + str( self.coeffs_decoded[13] ))
    
    def encode_coeffs_scaled(self):
        ''' 
        Encodes the scaled coefficients.        
        Operates on local variables.        
        '''                
        # Encode
        for i in range(len(self.coeffs_decoded_scaled)):
            if ('{:b}'.format(self.coeffs_decoded_scaled[i]).zfill(self.coeffs_encoded_length[i]+2)[0:3] == '100'): # check if MSB = "100"
                self.coeffs_encoded[i] = int( '1' + '{:b}'.format(self.coeffs_decoded_scaled[i]).zfill(self.coeffs_encoded_length[i]+2)[3:] , 2)
            elif ('{:b}'.format(self.coeffs_decoded_scaled[i]).zfill(self.coeffs_encoded_length[i]+2)[0:3] == '011'): # check if MSB = "011"
                self.coeffs_encoded[i] = int( '0' + '{:b}'.format(self.coeffs_decoded_scaled[i]).zfill(self.coeffs_encoded_length[i]+2)[3:] , 2)

        # Prints can be deleted after debug phase
        #print('coeff(ENCODED) vadc%d_submul'%self.number + ": " + str( self.coeffs_encoded[0] ))
        #print('coeff(ENCODED) vadc%d_st6_c1'%self.number + ": " + str( self.coeffs_encoded[1] ))
        #print('coeff(ENCODED) vadc%d_st6_c2'%self.number + ": " + str( self.coeffs_encoded[2] ))
        #print('coeff(ENCODED) vadc%d_st5_c1'%self.number + ": " + str( self.coeffs_encoded[3] ))
        #print('coeff(ENCODED) vadc%d_st5_c2'%self.number + ": " + str( self.coeffs_encoded[4] ))
        #print('coeff(ENCODED) vadc%d_st4_c1'%self.number + ": " + str( self.coeffs_encoded[5] ))
        #print('coeff(ENCODED) vadc%d_st4_c2'%self.number + ": " + str( self.coeffs_encoded[6] ))
        #print('coeff(ENCODED) vadc%d_st3_c1'%self.number + ": " + str( self.coeffs_encoded[7] ))
        #print('coeff(ENCODED) vadc%d_st3_c2'%self.number + ": " + str( self.coeffs_encoded[8] ))
        #print('coeff(ENCODED) vadc%d_st2_c1'%self.number + ": " + str( self.coeffs_encoded[9] ))
        #print('coeff(ENCODED) vadc%d_st2_c2'%self.number + ": " + str( self.coeffs_encoded[10] ))
        #print('coeff(ENCODED) vadc%d_st1_c1'%self.number + ": " + str( self.coeffs_encoded[11] ))
        #print('coeff(ENCODED) vadc%d_st1_c2'%self.number + ": " + str( self.coeffs_encoded[12] ))
        #print('coeff(ENCODED) vadc%d_st1_c3'%self.number + ": " + str( self.coeffs_encoded[13] ))

    def encode_coeffs(self):
        ''' 
        Encodes the scaled coefficients.        
        Operates on local variables.        
        '''                
        # Encode
        for i in range(len(self.coeffs_decoded)):
            if ('{:b}'.format(self.coeffs_decoded[i]).zfill(self.coeffs_encoded_length[i]+2)[0:3] == '100'): # check if MSB = "100"
                self.coeffs_encoded[i] = int( '1' + '{:b}'.format(self.coeffs_decoded[i]).zfill(self.coeffs_encoded_length[i]+2)[3:] , 2)
            elif ('{:b}'.format(self.coeffs_decoded[i]).zfill(self.coeffs_encoded_length[i]+2)[0:3] == '011'): # check if MSB = "011"
                self.coeffs_encoded[i] = int( '0' + '{:b}'.format(self.coeffs_decoded[i]).zfill(self.coeffs_encoded_length[i]+2)[3:] , 2)
 
    
    def rescale_coefficients(self, coeff_scale, scale_to_max=False, decode=True, encode=True, write=True, hook_read = None, hook_write = None):
        ''' 
        Note: Rescaling functions only after ADC calibration.
        Read ADC coefficients. Operates on memory map.  
        Decode ADC coefficients. Operates on local variables.
        Rescales ADC coefficients. Operates on local variables.
        Encode ADC coefficients. Operates on local variables.
        Write ADC coefficients. Operates on memory map.        
        '''        
        # Read
        self.read_coeffs( hook = hook_read )
        coeff_scale_choice = 0
        # Decode
        if decode:
            self.decode_coeffs()
        
        if scale_to_max == True:
            coeff_scale_choice = 65530.0 / ( (sum(self.coeffs_decoded[1:])+self.coeffs_decoded[0]*63/32) >> 3 )
            #print("ADC :"+str(self.number)+": Using scaling coefficient: "+ str(coeff_scale_choice)+ " for max code.")
        else:
            coeff_scale_choice = coeff_scale
            #print("ADC :"+str(self.number)+": Using scaling coefficient: "+ str(coeff_scale_choice)+ " for user defined max code.")
        
        
        # Rescale
        for i in range(len(self.coeffs_decoded)):        
            self.coeffs_decoded_scaled[i] = int( round( self.coeffs_decoded[i] * coeff_scale_choice ))          # important to round up.
        
        # Prints can be deleted after debug phase
        #print('coeff(DECODED+SCALED) vadc%d_submul'%self.number + ": " + str( self.coeffs_decoded_scaled[0] )) # TODO: Should submul be decoded?? scaled??.
        #print('coeff(DECODED+SCALED) vadc%d_st6_c1'%self.number + ": " + str( self.coeffs_decoded_scaled[1] ))
        #print('coeff(DECODED+SCALED) vadc%d_st6_c2'%self.number + ": " + str( self.coeffs_decoded_scaled[2] ))
        #print('coeff(DECODED+SCALED) vadc%d_st5_c1'%self.number + ": " + str( self.coeffs_decoded_scaled[3] ))
        #print('coeff(DECODED+SCALED) vadc%d_st5_c2'%self.number + ": " + str( self.coeffs_decoded_scaled[4] ))
        #print('coeff(DECODED+SCALED) vadc%d_st4_c1'%self.number + ": " + str( self.coeffs_decoded_scaled[5] ))
        #print('coeff(DECODED+SCALED) vadc%d_st4_c2'%self.number + ": " + str( self.coeffs_decoded_scaled[6] ))
        #print('coeff(DECODED+SCALED) vadc%d_st3_c1'%self.number + ": " + str( self.coeffs_decoded_scaled[7] ))
        #print('coeff(DECODED+SCALED) vadc%d_st3_c2'%self.number + ": " + str( self.coeffs_decoded_scaled[8] ))
        #print('coeff(DECODED+SCALED) vadc%d_st2_c1'%self.number + ": " + str( self.coeffs_decoded_scaled[9] ))
        #print('coeff(DECODED+SCALED) vadc%d_st2_c2'%self.number + ": " + str( self.coeffs_decoded_scaled[10] ))
        #print('coeff(DECODED+SCALED) vadc%d_st1_c1'%self.number + ": " + str( self.coeffs_decoded_scaled[11] ))
        #print('coeff(DECODED+SCALED) vadc%d_st1_c2'%self.number + ": " + str( self.coeffs_decoded_scaled[12] ))
        #print('coeff(DECODED+SCALED) vadc%d_st1_c3'%self.number + ": " + str( self.coeffs_decoded_scaled[13] ))

        # Encode
        if encode:
            self.encode_coeffs_scaled()
        
        # Write
        if write:
            self.write_coeffs( self.coeffs_encoded, hook = hook_write )
        
        return coeff_scale_choice

    def check_coeffs(self):
        ''' 
        Checks for missing codes.
        Requirement: sum of previous coeffs must be > than the next coeff.
        '''
        # submul * (63/32) < vadc%d_st6_c1 + 1  
        # vadc%d_st6_c1 * (127/63) <  vadc%d_st6_c2
        pass


class TX(object):
    
    def __init__(self, number, map=None):
        self.number = number
        self.map = map


    def start(self, hook=None):
        ''' 
        Starts TX channel.
        Operates on memory map, sets pulse reg and resets pulse reg in func.        
        '''
        if self.number < 8:
            regaddr = self.map.fields['tx_ch7_0_start'].fields[0]['addr']
            reg = self.map.registers[regaddr]
            
            self.map.fields['tx_ch7_0_start'].set_value(1<<self.number)
            hook(regaddr, reg.value, reg.fieldpos_list, reg.fieldval_list)                 
            self.map.fields['tx_ch7_0_start'].set_value(0)            
            
        else:
            regaddr = self.map.fields['tx8_start'].fields[0]['addr']
            reg = self.map.registers[regaddr]
            
            self.map.fields['tx8_start'].set_value(1)
            hook(regaddr, reg.value, reg.fieldpos_list, reg.fieldval_list)                 
            self.map.fields['tx8_start'].set_value(0)            

    def stop(self, hook=None):
        ''' 
        Stop TX channel.
        Operates on memory map, sets pulse reg and resets pulse reg in func.       
        '''
        if self.number < 8:
            regaddr = self.map.fields['tx_ch7_0_start'].fields[0]['addr']
            reg = self.map.registers[regaddr]
            
            self.map.fields['tx_ch7_0_stop'].set_value(1<<self.number)
            hook(regaddr, reg.value, reg.fieldpos_list, reg.fieldval_list)                 
            self.map.fields['tx_ch7_0_stop'].set_value(0)            
            
        else:
            regaddr = self.map.fields['tx8_stop'].fields[0]['addr']
            reg = self.map.registers[regaddr]
            
            self.map.fields['tx8_stop'].set_value(1)
            hook(regaddr, reg.value, reg.fieldpos_list, reg.fieldval_list)                 
            self.map.fields['tx8_stop'].set_value(0)
            
    def reset(self, hook=None):
        ''' 
        Reset TX channel.
        Operates on memory map, sets pulse reg and resets pulse reg in func.  
        '''
        if self.number < 8:
            regaddr = self.map.fields['tx_ch7_0_rst'].fields[0]['addr']
            reg = self.map.registers[regaddr]
            
            self.map.fields['tx_ch7_0_rst'].set_value(1<<self.number)
            hook(regaddr, reg.value, reg.fieldpos_list, reg.fieldval_list)                 
            self.map.fields['tx_ch7_0_rst'].set_value(0)            
            
        else:
            regaddr = self.map.fields['tx8_rst'].fields[0]['addr']
            reg = self.map.registers[regaddr]
            
            self.map.fields['tx8_rst'].set_value(1)
            hook(regaddr, reg.value, reg.fieldpos_list, reg.fieldval_list)                 
            self.map.fields['tx8_rst'].set_value(0)
   
    def set_tx_sources(self, *args):
        ''' 
        Sets the sources to be transmitted on the TX.        
        Operates on mamory map.
        '''                
        pass

    def set_tx_frame_type(self, ft):
        ''' 
        Sets the frme type for the TX channel
        Operates on mamory map.        
        '''                
        pass
    

class ACQ(object):
    
    def __init__(self, map=None):
        self.map = map


    def vadc_acq(self, value, hook=None):
        ''' 
        Starts ACQ for VADC.
        Operates on memory map, sets pulse reg and resets pulse reg in func.      
        '''
        regaddr = self.map.fields['acq_vadc_acq'].fields[0]['addr']
        reg = self.map.registers[regaddr]
        
        self.map.fields['acq_vadc_acq'].set_value(value)
        hook(regaddr, reg.value, reg.fieldpos_list, reg.fieldval_list)                 
        self.map.fields['acq_vadc_acq'].set_value(0)   

    def aadc_acq(self, hook=None):
        ''' 
        Starts ACQ for AADC.
        Operates on memory map, sets pulse reg and resets pulse reg in func.      
        '''
        regaddr = self.map.fields['acq_aadc_acq'].fields[0]['addr']
        reg = self.map.registers[regaddr]
        
        self.map.fields['acq_aadc_acq'].set_value(1)
        hook(regaddr, reg.value, reg.fieldpos_list, reg.fieldval_list)                 
        self.map.fields['acq_aadc_acq'].set_value(0)   
        
    def din_acq(self, hook=None):
        ''' 
        Starts ACQ for DIN.
        Operates on memory map, sets pulse reg and resets pulse reg in func.     
        '''
        regaddr = self.map.fields['acq_din_acq'].fields[0]['addr']
        reg = self.map.registers[regaddr]
        
        self.map.fields['acq_din_acq'].set_value(1)
        hook(regaddr, reg.value, reg.fieldpos_list, reg.fieldval_list)                 
        self.map.fields['acq_din_acq'].set_value(0)   

    def vadc_reset(self, hook=None):
        ''' 
        Reset ACQ for VADC.
        Operates on memory map, sets pulse reg and resets pulse reg in func.    
        '''
        regaddr = self.map.fields['acq_vadc_reset'].fields[0]['addr']
        reg = self.map.registers[regaddr]
        
        self.map.fields['acq_vadc_reset'].set_value(1)
        hook(regaddr, reg.value, reg.fieldpos_list, reg.fieldval_list)                 
        self.map.fields['acq_vadc_reset'].set_value(0)
   
    def aadc_reset(self, hook=None):
        ''' 
        Reset ACQ for AADC.
        Operates on memory map, sets pulse reg and resets pulse reg in func.        
        '''
        hook(self.map.fields['acq_aadc_acq'].fields[0]['addr'], int("10000000",2))  
    
    def din_reset(self, hook=None):
        ''' 
        Reset ACQ for DIN.
        Operates on memory map, sets pulse reg and resets pulse reg in func.      
        '''
        hook(self.map.fields['acq_din_reset'].fields[0]['addr'], int("10000000",2))


def populate_mm_rst_ioread_regs(MMRST, MF ):
    # SPI IO_READ registers with Testbench-based address space    
    MMRST.add_register(0xF000, "reg%d"%0xF000, 0) 
    MMRST.add_register(0xF001, "reg%d"%0xF001, 0)
    MMRST.add_register(0xF002, "reg%d"%0xF002, 0)
    MMRST.add_register(0xF003, "reg%d"%0xF003, 0)
    MMRST.add_register(0xF004, "reg%d"%0xF004, 0)
    MMRST.add_register(0xF005, "reg%d"%0xF005, 0)
    MMRST.add_register(0xF006, "reg%d"%0xF006, 0)
    MMRST.add_register(0xF007, "reg%d"%0xF007, 0)
    MMRST.add_register(0xF008, "reg%d"%0xF008, 0)
    MMRST.add_register(0xF009, "reg%d"%0xF009, 0)
    MMRST.add_register(0xF00A, "reg%d"%0xF00A, 0)

            
    MMRST.add_field(MemoryField(name = "IO_READ_DIN0", fields = [
                    MF.make_field_tuple(addr=0xF000, startbit=0, endbit=7, reset=0, romask=1, pumask=0, rrmask=0, wrxmask=0),
                 ], map = MMRST), value = 0
                 )
    MMRST.add_field(MemoryField(name = "IO_READ_DIN1", fields = [
                    MF.make_field_tuple(addr=0xF001, startbit=0, endbit=7, reset=0, romask=1, pumask=0, rrmask=0, wrxmask=0),
                 ], map = MMRST), value = 0
                 )
    MMRST.add_field(MemoryField(name = "IO_READ_DIN2", fields = [
                    MF.make_field_tuple(addr=0xF002, startbit=0, endbit=7, reset=0, romask=1, pumask=0, rrmask=0, wrxmask=0),
                 ], map = MMRST), value = 0
                 )    
    MMRST.add_field(MemoryField(name = "IO_READ_DIN3", fields = [
                    MF.make_field_tuple(addr=0xF003, startbit=0, endbit=7, reset=0, romask=1, pumask=0, rrmask=0, wrxmask=0),
                 ], map = MMRST), value = 0
                 )
    MMRST.add_field(MemoryField(name = "IO_READ_DIN4", fields = [
                    MF.make_field_tuple(addr=0xF004, startbit=0, endbit=7, reset=0, romask=1, pumask=0, rrmask=0, wrxmask=0),
                 ], map = MMRST), value = 0
                 )
    MMRST.add_field(MemoryField(name = "IO_READ_DIN5", fields = [
                    MF.make_field_tuple(addr=0xF005, startbit=0, endbit=7, reset=0, romask=1, pumask=0, rrmask=0, wrxmask=0),
                 ], map = MMRST), value = 0
                 )
    MMRST.add_field(MemoryField(name = "IO_READ_DIN6", fields = [
                    MF.make_field_tuple(addr=0xF006, startbit=0, endbit=7, reset=0, romask=1, pumask=0, rrmask=0, wrxmask=0),
                 ], map = MMRST), value = 0
                 )    
    MMRST.add_field(MemoryField(name = "IO_READ_DIN7", fields = [
                    MF.make_field_tuple(addr=0xF007, startbit=0, endbit=7, reset=0, romask=1, pumask=0, rrmask=0, wrxmask=0),
                 ], map = MMRST), value = 0
                 )
    MMRST.add_field(MemoryField(name = "IO_READ_PIRQ1", fields = [
                    MF.make_field_tuple(addr=0xF008, startbit=0, endbit=7, reset=0, romask=1, pumask=0, rrmask=0, wrxmask=0),
                 ], map = MMRST), value = 0
                 )                 
    MMRST.add_field(MemoryField(name = "IO_READ_PIRQ2", fields = [
                    MF.make_field_tuple(addr=0xF009, startbit=0, endbit=7, reset=0, romask=1, pumask=0, rrmask=0, wrxmask=0),
                 ], map = MMRST), value = 0
                 )                         
    MMRST.add_field(MemoryField(name = "IO_READ_IRQ", fields = [
                    MF.make_field_tuple(addr=0xF00A, startbit=0, endbit=7, reset=0, romask=1, pumask=0, rrmask=0, wrxmask=0),
                 ], map = MMRST), value = 0xff
                 )        
                 
def populate_mm_rst_spiregs(MMRST, MF ):
    # SPI registers with Testbench-based address space    
    MMRST.add_register(0xFA00, "reg%d"%0xFA00, 0) 
    MMRST.add_register(0xFA01, "reg%d"%0xFA01, 0)
    MMRST.add_register(0xFC00, "reg%d"%0xFC00, 0)
    
    # SPI _REG0              
    MMRST.add_field(MemoryField(name = "sys_clk_enable", fields = [
                    MF.make_field_tuple(addr=0xFA00, startbit=0, endbit=0, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0),
                 ], map = MMRST), value = 1
                 )
    MMRST.add_field(MemoryField(name = "seq_reset", fields = [
                    MF.make_field_tuple(addr=0xFA00, startbit=1, endbit=1, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0),
                 ], map = MMRST), value = 1
                 )
    MMRST.add_field(MemoryField(name = "seq_halt", fields = [
                    MF.make_field_tuple(addr=0xFA00, startbit=2, endbit=2, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0),
                 ], map = MMRST), value = 0
                 )
    
    # SPI_REG0              
    MMRST.add_field(MemoryField(name = "clk_div_mode", fields = [
                    MF.make_field_tuple(addr=0xFA01, startbit=0, endbit=1, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0),
                 ], map = MMRST), value = 0
                 )
    MMRST.add_field(MemoryField(name = "sysclk_dly", fields = [
                    MF.make_field_tuple(addr=0xFA01, startbit=2, endbit=3, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0),
                 ], map = MMRST), value = 0
                 )
    MMRST.add_field(MemoryField(name = "pll_enable", fields = [
                    MF.make_field_tuple(addr=0xFA01, startbit=4, endbit=4, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0),
                 ], map = MMRST), value = 0
                 )

    # SPI_RESET              
    MMRST.add_field(MemoryField(name = "system_reset", fields = [
                    MF.make_field_tuple(addr=0xFC00, startbit=0, endbit=3, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0),
                 ], map = MMRST), value = 0
                 )
    MMRST.add_field(MemoryField(name = "fifo_reset", fields = [
                    MF.make_field_tuple(addr=0xFC00, startbit=4, endbit=4, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0),
                 ], map = MMRST), value = 0
                 )

                 
def populate_mm_rst_busregs(MMRST, MF ):
    # Add empty registers for the bus system registers
    for addr in range(236):
        MMRST.add_register(addr, "reg%d"%addr, 0)  
    
    
    # Build logical fields into register map from csv file
    with open("bus_system_map.csv",'r') as csvfile:
        datareader = csv.reader(csvfile, delimiter=',')
        for i in range(13): next(datareader) # Skip first 13 rows
    
        for row in datareader:
            addr        = 0
            start_bit   = 0
            stop_bit    = 0
            readonly    = 0
            pulsereg    = 0
            readreset   = 0
            extreg      = 0        
            bitwidt     = row[7]
            resetval    = row[8]
            reg_type    = row[9] 
            
            # Determine start/stop bit         
            if(len(bitwidt)>1):
                start_bit=bitwidt.split(":")[1]
                stop_bit=bitwidt.split(":")[0]
            else:
                start_bit=bitwidt
                stop_bit=bitwidt  
    
            # Determine register type          
            if(reg_type=="r"):
                readonly=1        
            if(reg_type=="w/pulse"):
                pulsereg=1
            if(reg_type=="r/rst"):
                readreset=1 
            if(reg_type=="r/w/ext"):
                extreg=1 
            
            # Update address
            if(row[0] != "" and row[3] != "" and abs(int(row[3])) != abs(int(addr))):
                addr     = abs(int(row[3]))
            
            # Add registers as bitfields (skipping coeff_mem and instr_mem)
            if(row[0] != "" and row[7] != "" and row[0] != "coeff_mem" and row[0] != "instr_mem"):
               fieldname  = row[0]
               addr     = abs(int(row[3]))
               #print("Addr: "+str(addr)+" Reg: "+ fieldname.lower()+" startbit: "+start_bit+" stopbit: "+stop_bit+" reset: "+resetval)
               MMRST.add_field(MemoryField(name = fieldname, fields = [
                              MF.make_field_tuple(addr=addr, startbit=int(start_bit), endbit=int(stop_bit), reset=int(resetval), romask=int(readonly), pumask=int(pulsereg), rrmask=int(readreset), wrxmask=int(extreg)), 
                             ], map = MMRST), value = int(resetval)
                             )
            # Add bitfields
            if(row[6] != "" and row[7] != ""):
                fieldname  = row[6]
                addr     = abs(int(row[3]))
                #print("Addr: "+str(addr)+" Bitfield: "+ fieldname.lower()+" startbit: "+start_bit+" stopbit: "+stop_bit+" reset: "+resetval)       
                MMRST.add_field(MemoryField(name = fieldname, fields = [
                              MF.make_field_tuple(addr=addr, startbit=int(start_bit), endbit=int(stop_bit), reset=int(resetval), romask=int(readonly), pumask=int(pulsereg), rrmask=int(readreset), wrxmask=int(extreg)),
                             ], map = MMRST), value = int(resetval)
                             )
#        datareader.close()
        

def populate_mm_rst_coeffregs(MMRST, MF ):
    # Add empty registers for the adc coeff registers
    for i in range(1568)[1024:]:
        MMRST.add_register(i, "reg%d"%i, 0)
    
    # Adding ADC coefficients for all 17 ADCs
    base_addr=1024
    for i in range(17):         # Number of ADCs
        MMRST.add_field(MemoryField(name = "coeff_mem_"+str(0+32*i), fields = [
                    MF.make_field_tuple(addr=base_addr+0+32*i, startbit=0, endbit=7, reset=int("00001000",2), romask=0, pumask=0, rrmask=0, wrxmask=0), 
                    ], map = MMRST), value = int("00001000",2)
                    )
        MMRST.add_field(MemoryField(name = "coeff_mem_"+str(1+32*i), fields = [
                    MF.make_field_tuple(addr=base_addr+1+32*i, startbit=0, endbit=7, reset=int("01000001",2), romask=0, pumask=0, rrmask=0, wrxmask=0), 
                    ], map = MMRST), value = int("01000001",2)
                    )        
        MMRST.add_field(MemoryField(name = "coeff_mem_"+str(2+32*i), fields = [
                    MF.make_field_tuple(addr=base_addr+2+32*i, startbit=0, endbit=7, reset=int("00100000",2), romask=0, pumask=0, rrmask=0, wrxmask=0), 
                    ], map = MMRST), value = int("00100000",2)
                    )        
        MMRST.add_field(MemoryField(name = "coeff_mem_"+str(3+32*i), fields = [
                    MF.make_field_tuple(addr=base_addr+3+32*i, startbit=0, endbit=7, reset=int("00100000",2), romask=0, pumask=0, rrmask=0, wrxmask=0), 
                    ], map = MMRST), value = int("00100000",2)
                    )
        MMRST.add_field(MemoryField(name = "coeff_mem_"+str(4+32*i), fields = [
                    MF.make_field_tuple(addr=base_addr+4+32*i, startbit=0, endbit=7, reset=int("01000000",2), romask=0, pumask=0, rrmask=0, wrxmask=0), 
                    ], map = MMRST), value = int("01000000",2)
                    )
        MMRST.add_field(MemoryField(name = "coeff_mem_"+str(5+32*i), fields = [
                    MF.make_field_tuple(addr=base_addr+5+32*i, startbit=0, endbit=7, reset=int("00000000",2), romask=0, pumask=0, rrmask=0, wrxmask=0), 
                    ], map = MMRST), value = int("00000000",2)
                    )
        MMRST.add_field(MemoryField(name = "coeff_mem_"+str(6+32*i), fields = [
                    MF.make_field_tuple(addr=base_addr+6+32*i, startbit=0, endbit=7, reset=int("00000001",2), romask=0, pumask=0, rrmask=0, wrxmask=0), 
                    ], map = MMRST), value = int("00000001",2)
                    )
        MMRST.add_field(MemoryField(name = "coeff_mem_"+str(7+32*i), fields = [
                    MF.make_field_tuple(addr=base_addr+7+32*i, startbit=0, endbit=7, reset=int("00001000",2), romask=0, pumask=0, rrmask=0, wrxmask=0), 
                    ], map = MMRST), value = int("00001000",2)
                    )
        MMRST.add_field(MemoryField(name = "coeff_mem_"+str(8+32*i), fields = [
                    MF.make_field_tuple(addr=base_addr+8+32*i, startbit=0, endbit=7, reset=int("10000000",2), romask=0, pumask=0, rrmask=0, wrxmask=0), 
                    ], map = MMRST), value = int("10000000",2)
                    )
        MMRST.add_field(MemoryField(name = "coeff_mem_"+str(9+32*i), fields = [
                    MF.make_field_tuple(addr=base_addr+9+32*i, startbit=0, endbit=7, reset=int("00000000",2), romask=0, pumask=0, rrmask=0, wrxmask=0), 
                    ], map = MMRST), value = int("00000000",2)
                    )
        MMRST.add_field(MemoryField(name = "coeff_mem_"+str(10+32*i), fields = [
                    MF.make_field_tuple(addr=base_addr+10+32*i, startbit=0, endbit=7, reset=int("00010000",2), romask=0, pumask=0, rrmask=0, wrxmask=0), 
                    ], map = MMRST), value = int("00010000",2)
                    )
        MMRST.add_field(MemoryField(name = "coeff_mem_"+str(11+32*i), fields = [
                    MF.make_field_tuple(addr=base_addr+11+32*i, startbit=0, endbit=7, reset=int("00000000",2), romask=0, pumask=0, rrmask=0, wrxmask=0), 
                    ], map = MMRST), value = int("00000000",2)
                    )
        MMRST.add_field(MemoryField(name = "coeff_mem_"+str(12+32*i), fields = [
                    MF.make_field_tuple(addr=base_addr+12+32*i, startbit=0, endbit=7, reset=int("00000100",2), romask=0, pumask=0, rrmask=0, wrxmask=0), 
                    ], map = MMRST), value = int("00000100",2)
                    )
        MMRST.add_field(MemoryField(name = "coeff_mem_"+str(13+32*i), fields = [
                    MF.make_field_tuple(addr=base_addr+13+32*i, startbit=0, endbit=7, reset=int("00000000",2), romask=0, pumask=0, rrmask=0, wrxmask=0), 
                    ], map = MMRST), value = int("00000000",2)
                    )
        MMRST.add_field(MemoryField(name = "coeff_mem_"+str(14+32*i), fields = [
                    MF.make_field_tuple(addr=base_addr+14+32*i, startbit=0, endbit=7, reset=int("00000010",2), romask=0, pumask=0, rrmask=0, wrxmask=0), 
                    ], map = MMRST), value = int("00000010",2)
                    )
        MMRST.add_field(MemoryField(name = "coeff_mem_"+str(15+32*i), fields = [
                    MF.make_field_tuple(addr=base_addr+15+32*i, startbit=0, endbit=7, reset=int("00000000",2), romask=0, pumask=0, rrmask=0, wrxmask=0), 
                    ], map = MMRST), value = int("00000000",2)
                    )
        MMRST.add_field(MemoryField(name = "coeff_mem_"+str(16+32*i), fields = [
                    MF.make_field_tuple(addr=base_addr+16+32*i, startbit=0, endbit=7, reset=int("00000010",2), romask=0, pumask=0, rrmask=0, wrxmask=0), 
                    ], map = MMRST), value = int("00000010",2)
                    )                    
        MMRST.add_field(MemoryField(name = "coeff_mem_"+str(17+32*i), fields = [
                    MF.make_field_tuple(addr=base_addr+17+32*i, startbit=0, endbit=7, reset=int("00000000",2), romask=0, pumask=0, rrmask=0, wrxmask=0), 
                    ], map = MMRST), value = int("00000000",2)
                    )
        MMRST.add_field(MemoryField(name = "coeff_mem_"+str(18+32*i), fields = [
                    MF.make_field_tuple(addr=base_addr+18+32*i, startbit=0, endbit=2, reset=int("00000100",2), romask=0, pumask=0, rrmask=0, wrxmask=0), 
                    ], map = MMRST), value = int("00000100",2)
                    )    

def populate_mm_rst_ram(MMRST, MF ):
    # Add empty registers for the RAM registers
    # ... adding only even numbered addresses as it is not possible to read odd numbered addresses due to an ASIC bug.
    for i in range(8192,12290,2):
        MMRST.add_register(i, "reg%d"%i, 0)
    
    # Adding memory fields for all writable + readable RAM addresses
    # base_addr=8192
    for i in range(8192,12290,2):
        MMRST.add_field(MemoryField(name = "ram_8b_"+str(i), fields = [
                    MF.make_field_tuple(addr=i, startbit=0, endbit=7, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0), 
                    ], map = MMRST), value = 0
                    )
                    
def make_logical_fields(MMRST, MF ):
    """
    Note!   Currently only logical fields accross entire registers are supported.
            Logical fields accross bitfields in different registers are not supported.
    
    Makes logical fields:
        <logical_name>: <Brief description>
            reg<#>[<n>:<m>] (<bitfiled_name>) <LSB>
            reg<#>[<i>:<j>] (<bitfiled_name>) <MSB>

        odac0_dac: 10bit DAC value
            reg205[7:0] (odac0_dac_lo)
            reg206[1:0] (odac0_dac_hi)
            ...
        odac7_dac: 10bit DAC value
            reg220[7:0] (odac0_dac_lo)            
            reg219[1:0] (odac0_dac_hi)
        
        tx_ch0_source: Tx souces for Tx channel 0
            reg45[7:0] (tx_ch0_source_0)
            reg46[3:0] (tx_ch0_source_1)          
            ...
        tx_ch8_source: Tx souces for Tx channel 8
            reg61[7:0] (tx_ch8_source_0)
            reg62[3:0] (tx_ch8_source_1)          

        tx_data_reg0: Tx data register 0 (16 bit)
            reg63[7:0] (tx_data_reg0_0)
            reg64[7:0] (tx_data_reg1_0)          
            ...
        tx_data_reg3: Tx data register 3 (16 bit)
            reg69[7:0] (tx_data_reg0_0)
            reg70[3:0] (tx_data_reg1_0)          

        acq_vadc_en: ACQ VADC en
            reg89[7:0] (acq_vadc_en0)
            reg90[7:0] (acq_vadc_en1)          
        acq_vadc_lines: ACQ VADC lines to read
            reg92[7:0] (acq_vadc_lines0)
            reg93[7:0] (acq_vadc_lines1)          
        acq_vadc_columns: ACQ VADC columns to read
            reg94[7:0] (acq_vadc_columns0)
            reg95[7:0] (acq_vadc_columns1)     
        acq_vadc_frames: ACQ VADC frames to read
            reg96[7:0] (acq_vadc_frames0)
            reg97[7:0] (acq_vadc_frames1)   
        acq_aadc_loops: ACQ AADC loops to read
            reg102[7:0] (acq_aadc_loops0)
            reg103[7:0] (acq_aadc_loops1)  
        acq_din_loops: ACQ DIN loops to read
            reg108[7:0] (acq_din_loops0)
            reg109[7:0] (acq_din_loops1)  
            
        vadc_enable: VADC enable for VADC 15 (MSB) - 0 (LSB)
            reg203[7:0] (vadc_enable_1)
            reg204[7:0] (vadc_enable_2)   
                                                                       
        sys_aadc_vadc_tx_clk: Clock enable.     # Not yet supported!
            reg32[5:5] (tx_clk_en)
            reg123[0:0] (aadc_clk_en)
            reg123[4:4] (vadc_clk_en)
            reg64000[0:0] (sys_clk_enable)
        
        odac_int_sink_enable: Internal 3mA current sink enable for ODAC0 - 7
            reg229[8:0] (reserved_8b_1)                 
        idc_3b5dac: Idc DAC for 3b5 ADC stages
            reg231[7:4] (reserved_8b_2)
            reg230[1:0] (reserved_8b_1)
        iptat_3b5dac: Iptat DAC for 3b5 ADC stages
            reg230[5:0] (reserved_8b_1)                
        idc_2b5dac: Idc DAC for 2b5 ADC stages
            reg232[5:0] (reserved_8b_3)
        iptat_2b5dac: Iptat DAC for 2b5 ADC stages
            reg232[7:6] (reserved_8b_3)
            reg231[3:0] (reserved_8b_2)
            
        vadc0_submul: submul coefficient for vadc0
            reg1024[3:0] (coeff_mem_0[3:0])
        vadc0_st6_c1: st6_c1 coefficient for vadc0
            reg1024[7:4] (coeff_mem_0[7:4])
            reg1025[0:0] (coeff_mem_1[0:0])
        vadc0_st6_c2: st6_c2 coefficient for vadc0
            reg1025[6:1] (coeff_mem_1[6:1])
        vadc0_st5_c1: st5_c1 coefficient for vadc0
            reg1025[7:7] (coeff_mem_1[7:7])
            reg1026[5:0] (coeff_mem_2[5:0])
        vadc0_st5_c2: st5_c2 coefficient for vadc0
            reg1026[7:6] (coeff_mem_2[7:6])
            reg1027[5:0] (coeff_mem_3[5:0])            
        vadc0_st4_c1: st4_c1 coefficient for vadc0
            reg1027[7:6] (coeff_mem_3[7:6])
            reg1028[6:0] (coeff_mem_4[6:0])   
        vadc0_st4_c2: st4_c2 coefficient for vadc0
            reg1028[7:7] (coeff_mem_4[7:7])
            reg1029[7:0] (coeff_mem_5[7:0])               
            reg1030[0:0] (coeff_mem_6[0:0])
        vadc0_st3_c1: st3_c1 coefficient for vadc0             
            reg1030[7:1] (coeff_mem_6[7:1])                
            reg1031[3:0] (coeff_mem_7[3:0])                
        vadc0_st3_c2: st3_c2 coefficient for vadc0             
            reg1031[7:4] (coeff_mem_7[7:4]) 
            reg1032[7:0] (coeff_mem_8[7:0])                
        vadc0_st2_c1: st2_c1 coefficient for vadc0             
            reg1033[7:0] (coeff_mem_9[7:0]) 
            reg1034[4:0] (coeff_mem_10[4:0])
        vadc0_st2_c2: st2_c2 coefficient for vadc0             
            reg1034[7:5] (coeff_mem_10[7:5])             
            reg1035[7:0] (coeff_mem_11[7:0]) 
            reg1036[2:0] (coeff_mem_12[2:0])
        vadc0_st1_c1: st1_c1 coefficient for vadc0             
            reg1036[7:3] (coeff_mem_12[7:3])            
            reg1037[7:0] (coeff_mem_13[7:0])            
            reg1038[1:0] (coeff_mem_14[1:0])            
        vadc0_st1_c2: st1_c2 coefficient for vadc0             
            reg1038[7:2] (coeff_mem_14[7:2]) 
            reg1039[7:0] (coeff_mem_15[7:0])            
            reg1040[1:0] (coeff_mem_16[1:0])
        vadc0_st1_c3: st1_c3 coefficient for vadc0             
            reg1040[1:0] (coeff_mem_16[1:0])            
            reg1041[7:0] (coeff_mem_17[7:0]) 
            reg1042[2:0] (coeff_mem_18[2:0])
            ... skipping not used reg1043 - reg1053 ...
        
        vadc1_submul: submul coefficient for vadc0
            reg1054[3:0] (coeff_mem_32[3:0])
            ... pattern continues to aadc.
    """    
                    
    # ODAC
    for i in range(8):
        MMRST.add_field(MemoryField(name = "odac%d_dac"%i, fields = [
                        MF.make_field_tuple(addr=206+i*2, startbit=0, endbit=7, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                        MF.make_field_tuple(addr=205+i*2, startbit=0, endbit=1, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                     ], map = MMRST), value = 0
                     )
    
    # TX sources
    for i in range(8):
        MMRST.add_field(MemoryField(name = "tx_ch%d_source"%i, fields = [
                        MF.make_field_tuple(addr=45+i*2, startbit=0, endbit=7, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                        MF.make_field_tuple(addr=46+i*2, startbit=0, endbit=3, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                     ], map = MMRST), value = 0
                     )
                
    # TX data regs
    for i in range(3):
        MMRST.add_field(MemoryField(name = "tx_data_reg%d"%i, fields = [
                        MF.make_field_tuple(addr=63+i*2, startbit=0, endbit=7, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                        MF.make_field_tuple(addr=64+i*2, startbit=0, endbit=7, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                     ], map = MMRST), value = 0
                     )              
                    
    # ACQ enable columns lines and frames 
    MMRST.add_field(MemoryField(name = "acq_vadc_en", fields = [
                    MF.make_field_tuple(addr=89, startbit=0, endbit=7, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                    MF.make_field_tuple(addr=90, startbit=0, endbit=7, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                 ], map = MMRST), value = 0
                 )
    MMRST.add_field(MemoryField(name = "acq_vadc_lines", fields = [
                    MF.make_field_tuple(addr=92, startbit=0, endbit=7, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                    MF.make_field_tuple(addr=93, startbit=0, endbit=7, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                 ], map = MMRST), value = 0
                 )
    MMRST.add_field(MemoryField(name = "acq_vadc_columns", fields = [
                    MF.make_field_tuple(addr=94, startbit=0, endbit=7, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                    MF.make_field_tuple(addr=95, startbit=0, endbit=7, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                 ], map = MMRST), value = 0
                 )                     
    MMRST.add_field(MemoryField(name = "acq_vadc_frames", fields = [
                    MF.make_field_tuple(addr=95, startbit=0, endbit=7, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                    MF.make_field_tuple(addr=96, startbit=0, endbit=7, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                 ], map = MMRST), value = 0
                 )
    MMRST.add_field(MemoryField(name = "acq_aadc_loops", fields = [
                    MF.make_field_tuple(addr=102, startbit=0, endbit=7, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                    MF.make_field_tuple(addr=103, startbit=0, endbit=7, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                 ], map = MMRST), value = 0
                 ) 
    MMRST.add_field(MemoryField(name = "acq_din_loops", fields = [
                    MF.make_field_tuple(addr=108, startbit=0, endbit=7, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                    MF.make_field_tuple(addr=109, startbit=0, endbit=7, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                 ], map = MMRST), value = 0
                 )                       
    # VADC enable
    MMRST.add_field(MemoryField(name = "vadc_enable", fields = [
                    MF.make_field_tuple(addr=203, startbit=0, endbit=7, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                    MF.make_field_tuple(addr=204, startbit=0, endbit=7, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                 ], map = MMRST), value = 0
                 )
                 
    # Clocks enable
    # MMRST.add_field(MemoryField(name = "sys_aadc_vadc_tx_clk", fields = [
                    # MF.make_field_tuple(addr=32, startbit=5, endbit=5, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1), #LSB
                    # MF.make_field_tuple(addr=123, startbit=0, endbit=0, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                    # MF.make_field_tuple(addr=123, startbit=4, endbit=4, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                    # MF.make_field_tuple(addr=64000, startbit=0, endbit=0, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1), #MSB
                 # ], map = MMRST), value = 0
                 # )
    
    # ODAC internal current sink enable
    MMRST.add_field(MemoryField(name = "odac_int_sink_enable", fields = [
                    MF.make_field_tuple(addr=229, startbit=0, endbit=7, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                 ], map = MMRST), value = 0
                 )
    # Idc / Iptat dacs
    MMRST.add_field(MemoryField(name = "idc_3b5dac", fields = [
                    MF.make_field_tuple(addr=231, startbit=4, endbit=7, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                    MF.make_field_tuple(addr=230, startbit=0, endbit=1, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                 ], map = MMRST), value = 0
                 )
    MMRST.add_field(MemoryField(name = "iptat_3b5dac", fields = [
                    MF.make_field_tuple(addr=230, startbit=2, endbit=7, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                 ], map = MMRST), value = 0
                 )
    MMRST.add_field(MemoryField(name = "idc_2b5dac", fields = [
                    MF.make_field_tuple(addr=232, startbit=0, endbit=5, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                 ], map = MMRST), value = 0
                 )
    MMRST.add_field(MemoryField(name = "iptat_2b5dac", fields = [
                    MF.make_field_tuple(addr=232, startbit=6, endbit=7, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                    MF.make_field_tuple(addr=231, startbit=0, endbit=3, reset=0, romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                 ], map = MMRST), value = 0
                 )                 
    
    # VADC0 - VADC16 + AADC calibration coefficients
    for i in range(17):         # Number of ADCs
        # vadc0_submul
        MMRST.add_field(MemoryField(name = "vadc%d_submul"%i, fields = [
                        MF.make_field_tuple(addr=1024+0+32*i, startbit=0, endbit=3, reset=int("1000",2), romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                     ], map = MMRST), value = int("1000",2)
                     )    
        MMRST.add_field(MemoryField(name = "vadc%d_st6_c1"%i, fields = [
                        MF.make_field_tuple(addr=1024+0+32*i, startbit=4, endbit=7, reset=int("0000",2), romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                        MF.make_field_tuple(addr=1024+1+32*i, startbit=0, endbit=0, reset=int("1",2), romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                     ], map = MMRST), value = int("10000",2)
                     )        
        MMRST.add_field(MemoryField(name = "vadc%d_st6_c2"%i, fields = [
                        MF.make_field_tuple(addr=1024+1+32*i, startbit=1, endbit=6, reset=int("100000",2), romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                     ], map = MMRST), value = int("100000",2)
                     )        
        MMRST.add_field(MemoryField(name = "vadc%d_st5_c1"%i, fields = [
                        MF.make_field_tuple(addr=1024+1+32*i, startbit=7, endbit=7, reset=int("0",2), romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                        MF.make_field_tuple(addr=1024+2+32*i, startbit=0, endbit=5, reset=int("100000",2), romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                     ], map = MMRST), value = int("1000000",2)
                     )     
        MMRST.add_field(MemoryField(name = "vadc%d_st5_c2"%i, fields = [
                        MF.make_field_tuple(addr=1024+2+32*i, startbit=6, endbit=7, reset=int("00",2), romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                        MF.make_field_tuple(addr=1024+3+32*i, startbit=0, endbit=5, reset=int("100000",2), romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                     ], map = MMRST), value = int("10000000",2)
                     )
        MMRST.add_field(MemoryField(name = "vadc%d_st4_c1"%i, fields = [
                        MF.make_field_tuple(addr=1024+3+32*i, startbit=6, endbit=7, reset=int("00",2), romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                        MF.make_field_tuple(addr=1024+4+32*i, startbit=0, endbit=6, reset=int("1000000",2), romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                     ], map = MMRST), value = int("100000000",2)
                     )                     
        MMRST.add_field(MemoryField(name = "vadc%d_st4_c2"%i, fields = [
                        MF.make_field_tuple(addr=1024+4+32*i, startbit=7, endbit=7, reset=int("0",2), romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                        MF.make_field_tuple(addr=1024+5+32*i, startbit=0, endbit=7, reset=int("00000000",2), romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                        MF.make_field_tuple(addr=1024+6+32*i, startbit=0, endbit=0, reset=int("1",2), romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                     ], map = MMRST), value = int("1000000000",2)
                     )
        MMRST.add_field(MemoryField(name = "vadc%d_st3_c1"%i, fields = [
                        MF.make_field_tuple(addr=1024+6+32*i, startbit=1, endbit=7, reset=int("0000000",2), romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                        MF.make_field_tuple(addr=1024+7+32*i, startbit=0, endbit=3, reset=int("1000",2), romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                     ], map = MMRST), value = int("10000000000",2)
                     )
        MMRST.add_field(MemoryField(name = "vadc%d_st3_c2"%i, fields = [
                        MF.make_field_tuple(addr=1024+7+32*i, startbit=4, endbit=7, reset=int("0000",2), romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                        MF.make_field_tuple(addr=1024+8+32*i, startbit=0, endbit=7, reset=int("10000000",2), romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                     ], map = MMRST), value = int("100000000000",2)
                     )
        MMRST.add_field(MemoryField(name = "vadc%d_st2_c1"%i, fields = [
                        MF.make_field_tuple(addr=1024+9+32*i, startbit=0, endbit=7, reset=int("00000000",2), romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                        MF.make_field_tuple(addr=1024+10+32*i, startbit=0, endbit=4, reset=int("10000",2), romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                     ], map = MMRST), value = int("1000000000000",2)
                     )
        MMRST.add_field(MemoryField(name = "vadc%d_st2_c2"%i, fields = [
                        MF.make_field_tuple(addr=1024+10+32*i, startbit=5, endbit=7, reset=int("000",2), romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                        MF.make_field_tuple(addr=1024+11+32*i, startbit=0, endbit=7, reset=int("00000000",2), romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                        MF.make_field_tuple(addr=1024+12+32*i, startbit=0, endbit=2, reset=int("100",2), romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                     ], map = MMRST), value = int("10000000000000",2)
                     )
        MMRST.add_field(MemoryField(name = "vadc%d_st1_c1"%i, fields = [
                        MF.make_field_tuple(addr=1024+12+32*i, startbit=3, endbit=7, reset=int("00000",2), romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                        MF.make_field_tuple(addr=1024+13+32*i, startbit=0, endbit=7, reset=int("00000000",2), romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                        MF.make_field_tuple(addr=1024+14+32*i, startbit=0, endbit=1, reset=int("10",2), romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                     ], map = MMRST), value = int("100000000000000",2)
                     )
        MMRST.add_field(MemoryField(name = "vadc%d_st1_c2"%i, fields = [
                        MF.make_field_tuple(addr=1024+14+32*i, startbit=2, endbit=7, reset=int("000000",2), romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                        MF.make_field_tuple(addr=1024+15+32*i, startbit=0, endbit=7, reset=int("00000000",2), romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                        MF.make_field_tuple(addr=1024+16+32*i, startbit=0, endbit=1, reset=int("10",2), romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                     ], map = MMRST), value = int("1000000000000000",2)
                     )
        MMRST.add_field(MemoryField(name = "vadc%d_st1_c3"%i, fields = [
                        MF.make_field_tuple(addr=1024+16+32*i, startbit=2, endbit=7, reset=int("000000",2), romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                        MF.make_field_tuple(addr=1024+17+32*i, startbit=0, endbit=7, reset=int("00000000",2), romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                        MF.make_field_tuple(addr=1024+18+32*i, startbit=0, endbit=2, reset=int("100",2), romask=0, pumask=0, rrmask=0, wrxmask=0, logical=1),
                     ], map = MMRST), value = int("10000000000000000",2)
                     )  
                     
# Build up memory map of NIRCA MkII with reset values
MMRST = MemoryMap()
MF = MemoryField(map = MMRST)

# SPI registers
populate_mm_rst_spiregs(MMRST, MF)

# SPI IO_READ registers
populate_mm_rst_ioread_regs(MMRST, MF)

# Bus registers
populate_mm_rst_busregs(MMRST, MF)

# coeff_mem
populate_mm_rst_coeffregs(MMRST, MF)

# instr_mem 
populate_mm_rst_ram(MMRST, MF)

# Make logical fields
make_logical_fields(MMRST, MF)
#print(make_logical_fields.__doc__)