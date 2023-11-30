# -*- coding: utf-8 -*-
# ... For /usr/bin/python2.6
"""
This module defines the :class:`nirca_parser` class, and a small error handler class :class:`perr`.
"""


# TODO-memo's:
# At the moment this code is somewhat flat, it should be considered to structure some parts better, e.g. syntax checking. 

import re       # Regular expressions
import os.path as path
import sys
import itertools

class perr: # Error handler
    """
    Implements a simple error handler class.
    """
    errors = 0
    warnings = 0
    infos = 0
    exit_level = 3  # Exit on fatal
    # exit_level = 2    # Exit on error
    silent = 0
    def __init__(self):
        """
        Construct a new error handler object.
        """
        errors = 0
        warnings = 0
        infos = 0
    def fatal(self, source, msg):
        """
        Handles fatal errors.

         *source* The part of the program (parser, linker, disassembler) that reported the error.

         *msg* The error message.
        
         *Returns* No return, calls system exit with error code 1.
        """
        print(f"{source} Fatal Error : {msg}")
        sys.exit(1)
    def exit_handler(self, level):
        """
        Exit handler. Determines if sys.exit() is called based on the error severity *level*. 

         *Returns* No return, may call system exit with error code 1.
        """
        if level>=self.exit_level:
            print("Exiting...")
            sys.exit(1)

    def error(self, source, msg):
        """
        Handles errors (severity level 2).

         *source* The part of the program (parser, linker, disassembler) that reported the error.

         *msg* The error message.
        
         *Returns* No return, may call system exit with error code 1.
        """
        if not self.silent : print(f"{source} Error : {msg}")
        self.errors = self.errors + 1
        raise Exception
        self.exit_handler(2)
    def warn(self, source, msg):
        """
        Handles warnings (severity level 1).

         *source* The part of the program (parser, linker, disassembler) that reported the error.

         *msg* The error message.
        
         *Returns* No return, may call system exit with error code 1.
        """
        if not self.silent : print(f"{source} Warning : {msg}")
        self.warnings = self.warnings + 1
        self.exit_handler(1)
    def info(self, source, msg):
        """
        Handles information (severity level 0).

         *source* The part of the program (parser, linker, disassembler) that reported the error.

         *msg* The error message.
        
         *Returns* No return, may call system exit with error code 1.
        """
        if not self.silent : print(f"{source} Info : {msg}")
        self.infos = self.infos + 1

e = perr() # Create error handler instance

# Tables for symbols
# asm_opcodes is a dictionary to translate assembler command to internal variant, so one can use alternate naming (shorthand names)/change the naming later.

class nirca_parser: # Input file reader
    """
Class implementing the NIRCA assembler parser and linker. 

A NIRCA assembler file is composed of lines, each line is either empty,  a sequencer instructions, or a definition of a constant.
 
**Assembler line syntax:**

.. code-block:: bash

  [@<symbol>:] [OPCODE operand1 [,] operand2 ... ]] # Comment

A ``#`` and any following text character is treated as a comment.

Braces above are not part of syntax but specify:
  ``<>`` - required

  ``[]`` - optional

Syntax notes: 

 * The character ``,`` between operands is treated the same as whitespace.

Known issues:

 * The parser uses a very simple method of grabbing tokens from a line. It is therefore important to avoid spaces within operands that use ``[]`` braces for register/memory selection. 

Sample program:

.. code-block:: bash

 # Simple clock vector output manipulation

 # Constants :

 $rows = 4                      # A constant 
 $cols = 4                      # A constant 
 $repetitions = ($ROWS*$COLS)   # A derived constant 

 # Instructions :

 @Start:                               # Address symbol
               MOVV VM[0]              # Move vector memory row 0 to vector registers (32-bits)
               CALL @Loop1             # Store state on stack and set up *delayed* branch to location @Loop1 
               LOAD LC, $repetitions   # Loads the loop counter (LC) so call above performs $repetition loops, then branch
               JUMP @Start             # Endless repetions

 @Loop1:                               # Address Symbol 
       SYNC    MOVV  VM[1]             # Switch to vector 2, after SYNC strobe 
       SYNC    MOVV  VM[2]             # Switch to vector 2, after SYNC strobe
               LOOPR @Loop1            # Decrements LC and loops to @Loop1 if LC>0, else pop stack and return (will restore LC, IP).

*Testing the program with the simulator*

 ``[hberge@ADELE simple]$ ../../nirca-asm.py -cycles 20 -sim simple.nasm``

:any:`nirca-asm` output to stdout:

.. code-block:: bash

 Simulator Info : Importing simulator class
 Constants Table = {
    COLS : 4
    MAX_NOOP : 255
    REPETITIONS : 16
    ROWS : 4
 }

    * Symbol table :
    
                             Symbol     CMD_NO    LINE_NO  ALIGNMENT 
                             @Start          0         11          8          0 
                             @Loop1          4         17          8          8 

    * cmds[] =
    
 SYNC OPCODE                         DESTINATION          SOURCE CMD_NO LINE_NO ALIGN ADDRESS     Binary code
       MOVV                        [None, None]       ['VM', 0]      0      12     8       0 110000000000000
       CALL                          ['@Loop1']               -      1      13     1       1 010000000000001
         LD                        ['LC', None]   ['const', 16]      2      14     1       2 000000000010000
       JUMP                          ['@Start']               -      3      15     1       3 010100000000000
   S   MOVV                        [None, None]       ['VM', 1]      4      18     8       8 110010000000001
   S   MOVV                        [None, None]       ['VM', 2]      5      19     1       9 110010000000010
      LOOPR                          ['@Loop1']               -      6      20     1      10 100100000000001
 Simulator Info : reset()
 Simulator Info : simulate()
     0 MOVV            0  0 
     1 CALL            1  0 
     2 <flush>        16  0 
     8 MOVV            1  1 
     9 MOVV            2  1 
    10 LOOPR           1  0 
    11 <flush>         0  0 
     2 LDCC           16  0 
     3 JUMP            0  0 
     4 <flush>         0  0 
     0 MOVV            0  0 
     1 CALL            1  0 
     2 <flush>        16  0 
     8 MOVV            1  1 
     9 MOVV            2  1 
    10 LOOPR           1  0 
    11 <flush>         0  0 
     8 MOVV            1  1 
     9 MOVV            2  1 
    10 LOOPR           1  0 


Please see the documentation for more information regarding the opcodes. 

"""
    # Opcode translation table (repeated codes for shorthand opcodes, only 1 internal NOOP function)
    asm_opcodes = {
#        'ACQ'     : 'ACQ',
        'CALL'    : 'CALL',
        'CLF'     : 'CLF',
        'J'       : 'JUMP',
        'JC'      : 'JUMPC',
        'JI'      : 'JUMPI',
        'JUMP'    : 'JUMP',
        'JUMPC'   : 'JUMPC',
        'JUMPI'   : 'JUMPI',
        'LD'      : 'LD',
        'LDCC'      : 'LDCC',
        'LDNC'      : 'LDNC',
        'LDTEMP'  : 'LDTEMP',
        'LOAD'    : 'LD',
        'LDREG'    : 'LD',
        'LOOP'    : 'LOOP',
        'LOOPR'   : 'LOOPR',
        'RETURN'  : 'RETURN', 
        'MOVD'    : 'MOVD',
        'MOVTEMP' : 'MOVTEMP',
        'NOOP'    : 'NOOPC',
        'NOOPC'   : 'NOOPC',
        'SDTX'    : 'SDTX',
        'SDTXW'   : 'SDTXW',
        'SETF'    : 'SETF',
#        'SYNC'    : 'SYNC',
        'TXBR'    : 'TXBR',
        'TXTEMP'  : 'TXTEMP',
        'TXVAL'   : 'TXVAL',
        'WAIT'    : 'WAIT',
        'unused0' : 'unused0',
        'unused1' : 'unused1',
        'unused2' : 'unused2',
        'unused3' : 'unused3'
        }
    # Opcode flags
    opcode_flags = {
            'A'     : 'A',
            'B'     : 'B',
            'K'     : 'K',
            'S'     : 'S'
            }
    # Register translation table for LD operation
    LD_reg_trans = {
            'BAR'   : 'REG0',
            'AR'    : 'REG1',
            'CR'    : 'REG2',
            'SP'    : 'REG3',
            'DOR'   : 'REG4',
            'VR'    : 'REG4',
            'TEMP'  : 'REG5',
            'SPFR'  : 'REG6',
            'unused_REG7' : 'REG7'
            } # TODO: add test of number of bits in LDREG commands 
    
    # tab_opcodes is used to allow grouped instructions so LD will cover all load commands, and so on, for the sequencer. 
    # SYNC,ACQ is not an instruction, but affects the SYNC-field of the next instruction
    
    tab_opcodes = ['LD', 'MOVD', 'CALL', 'LOOP', 'LOOPR', 'RETURN', 
                'SETF', 'CLF', 'SDTX', 'SDTXW', 'WAIT',
                'JUMP', 'JUMPC', 'JUMPI', 'NOP', 'LDTEMP', 'TXTEMP', 
                'TXVAL','TXBR', 'unused0', 'unused1', 'unused2', 'unused3',
                'SYNC', 'ACQ'
                ] # Internal intermediate instruction names
    
    # Machine Instruction Codes:
    # Tuple fields are:
    #    (s_mcode=0 , u_syncbits=1 , u_bits_regsel=2, s_infix_def=3, u_val_bits=4 )
    # The string code for LD operations are concatenated 'LD'+REG_name_str
    CodeTable = {
        'LDCC'    : ('000',     '',    0, '',           12),
        'LDNC'    : ('001',     '',    0, '',           12),
        'CALL'    : ('01000',   '',    0, '',           10),
        'JUMP'    : ('01001',   '',    0, '',           10),
        'JUMPC'   : ('01010',   '',    0, '',           10),
        'JUMPI'   : ('01011',   '',    0, '',           10),
        'LOOP'    : ('01100',   '',    0, '',           10),
        'LOOPR'   : ('01101',   '',    0, '',           10),
        'RETURN'  : ('0111000', '',    0, '00000000',   0),    
        'unused0' : ('0111001', '',    0, '',           8),
        'SETF'    : ('0111010', '',    0, '',           8),
        'CLF'     : ('0111011', '',    0, '',           8),
        'SDTX'    : ('0111100', '',    0, '',           8),
        'SDTXW'   : ('0111101', '',    0, '',           8),
        'unused1' : ('0111110', '',    0, '',           8),
        'WAIT'    : ('0111111', '',    0, '',           8),
        'LDREG'   : ('10',      'SA',  3, '',           8),
        'MOVD'    : ('1100',    'BSA', 0, '',           8),
        'NOOPC'   : ('1101',    'BSA', 0, '',           8),

        'TXVAL'   : ('111000',  'K',   0, '',           8),
        'TXTEMP'  : ('111001',  'K',   0, '00000000',   0),
        'LDTEMP'  : ('111010',  'B',   0, '00000000',   0),
        'TXBR'    : ('111011',  'B',   0, '00000000',   0),

        'MOVTEMP' : ('111100',  'B',   0, '00000000',   0),
        'unused2' : ('111101',  '',    0, '',           9),
        'unused3' : ('11111',   '',    0, '',           10)
        #'TXK'     : ('1111001', '',    0, '',         8),  #
        #'TXCC'    : ('1111010', '',    0, '',         8),  #
        #'unused6' : ('1111100', '',    0, '',         8),  #
        #'TXAUX'   : ('1111101', '',    0, '',         8),  #
        #'TXDIN'   : ('1111110', '',    0, '',         8),  #
    }

    cmds=[]     # cmd is a list that holds commands, parameters, flags-bit, and info: 
    # Fields used in cmds
    cf_flags   = 0 # Flag bits, if contains 'S' then SYNC, 'SA' then SYNC+ACQ, 'A' then ACQ, 'C' increment BAR:AR, 'K' TX as K-char
    cf_opcode  = 1 # One of tab_opcodes, except 'SYNC' & 'ACQ'
    cf_params  = 2 # 1 or 2 operands: [[base/type, index/value]] or [[destbase/type, index/value], [srcbase/type, index/value]]
    cf_cmd_no  = 3 # Command number
    cf_line_no = 4 # Line number in input file
    cf_align   = 5 # Alignment (8 if address is branched to, 1 otherwise)
    cf_addr    = 6 # Address (after linker)
    cf_code    = 7 # Machine code output (
    
    symbols={}  # symbol dictionary for assistance when doing addresses
    # Fields used in symbols
    sf_cmd_no  = 0 # Command number (reference to cmds[])
    sf_line_no = 1 # Line number in input file
    sf_align   = 2 # Alignment (for linker)
    sf_addr    = 3 # Address (after linker / output)
    
    constants={"MAX_NOOP": 255} # Dictionary to hold pre- & user-defined constants


    def __init__(self, inf):
        """
        Parameters:
        inf - text (.nasm) input file opened for reading
        parses include of other files
        """
        self.symbols = {}                                       # AHA: Initializing symbols to avoid duplicate symbols when calling write_mco_8b_testbench
        self.cmds =  []                                         # AHA: Initializing cmds to avoid duplicate cmds when calling write_mco_8b_testbench
        self.debug = 1
        self.lines  = []
        self.lines  = list(enumerate(inf.readlines()))          # Read all lines from input file
        self.constants = {"MAX_NOOP": 255}                      # AHA: Initializing constants to avoid duplicates when calling write_mco_8b_testbench
        
        ## I am not a Python programmer ==> just generate a new list in the same way and clear it >>>
        ## and then rebuild the structure and always append at the end ==> either the command or the read file lines ...
        xlines = []
        xlines = list(enumerate(inf.readlines()))
        del xlines[0:len(xlines)-1]

        """ Added hack to have include files ! TODO : it would be better to have a recursive parser, but (=work) """
        include_limit=100
        included_files=0
        for i, l in self.lines:
            l=l.strip()
            # print (">>>> %4d:"%i) + l # AHA commented out to avoid having this info on the staus line in testbench.
            #mo = re.match(r"'include\s+\"", l)
            #mo = re.match(r"'include\s+\"([^\"]*)\"", l)
            mo = re.match(r"'include\s+\"([^\"]*)\"(\s+)?(#.*)?$", l)
            if mo:
                # e.info("init", "Including file %s (flat)" % mo.group(1)) # AHA commented out to avoid having this info on the staus line in testbench.
                try:
                    incfile = open(path.expandvars(mo.group(1)),'r')    # Last argument is input file
                except:
                    print(f"Could not open input file {mo.group(1)} for read")
                    e.fatal("init", "File I/O error") # Die
                ## -------------------------------------------------------------------------------    
                temp=[]
                temp = list(enumerate(incfile.readlines()))    # Read all lines from include file
                # for k, x in temp: print("<< %d "%k) + x      # AHA: Removed printing to avoid clutter in Testbench Script Output
                xlines.extend(temp)
                ###-------------------------------------------------------------------------------
##                selfx.lines[i:(i+1)] = temp                     # Replace include with all lines read
                included_files = included_files+1
                if included_files > include_limit:
                    e.fatal("init", "Exceeded soft include limit of %d files" % include_limit) # Die
            else:
                xlines.append(self.lines[i]) ## FE : append the non include lines
                
        self.lines = xlines ## and finally overwrite the original lines list
        
    def parser_regcheck(self,str):
        """
        Method to test validity of register names (and optionally index) found in operand.
        """
        # For use with LD commands only - TODO-? but no other command needs this
    
        # Translate special register names (if applicable)
        if str in self.LD_reg_trans:
            str = self.LD_reg_trans.get(str)
            #print str
    
        base = re.match(r"([a-zA-Z]+)[\[\(]?([0-9a-fx+\-*/]+)?[\]\)]?",str) # Base name
        reg_sel=''
        if base:
            if len(base.groups())>1:
                reg_sel=base.group(2)
            if reg_sel:
                try:
                    reg_sel=eval(reg_sel)
                except ValueError:
                    e.error("Parser", "Invalid register index '%s' in %s at line %d" % (reg_sel, str, line_no) )
    
            base = base.group(1)
        else:
            e.error("Parser", "Invalid register (%s) at line %d" % (str, line_no) )
            return 0
    
        base_match = {
                'CC'  : 'CC',
                'NC'  : 'NC',
                'LC'  : 'CC',
                'CLC' : 'CC',
                'NLC' : 'NC',
                'REG' : 'REG',
                }.get(base, '')

        if reg_sel:     
            if base_match == 'CC' or base_match == 'NC':
                if not (reg_sel>=0 and reg_sel<= 0):
                    e.error("Parser","CC/NC do not have sub-registers. Found index %s at line %d" % (reg_sel, line_no) )
            if base_match == 'REG':
                if not (reg_sel>=0 and reg_sel<=7): #>= 0) and (reg_sel<=7)):
                    e.error("Parser", "REG selector out of range (0,7) found %s at line %d" % (reg_sel, line_no) )
            
        return [base_match, reg_sel]
    
    def replace_var_const(self, expr):
        """
        Replace $constants with value from the constants table.
        """
        # print "replace_var_const called with:", expr # debug
        matchobj = re.findall(r"\$(\w+)",expr)
        if not matchobj:
            return expr
        else:
            for mog in matchobj: #.groups():
                try:
                    cdef = self.constants[mog.upper()]
                    expr = re.sub("\$"+mog, str(cdef) , expr, count=1)
                except:
                    e.error("Parser","Invalid index constant %s." % (mog))
                    raise ValueError 
        # print "rep_var_const yielded ", expr # debug
        return expr


    def parser_srccheck(self, str, allowed_bases, maxbits, line_no):
        """Test if source operand string e.g. "VM[12]" has valid base and index.
 
        Require index < 2**maxbits-1
        """
        #print str
        base = ''
        value = ''
        if re.match(r"^[A-Za-z]", str):
            base = re.sub(r"([A-Za-z]+).*",r"\1", str)
        #print line_no, base
        if base:
            if not base in allowed_bases:
                e.error("Parser","Invalid base for source found %s on line %d" % (base, line_no))
            else:
                index_part = re.sub(base+r"[\(\[\{]{1}(.*)[\)\]\}]{1}\s*", r"\1", str)
                #print index_part
                try: 
                    index_part = self.replace_var_const(index_part)
                    value = eval(index_part)
                except: 
                    e.error("Parser","Error encountered while evaluating %s on line %d" % (index_part, line_no))
            
        elif 'const' in allowed_bases:          
            base = 'const'
            try:
                str = self.replace_var_const(str)
                value = eval(str)
            except ValueError:
                e.error("Parser","Error encountered while evaluating %s on line %d" % (str, line_no))

            if value:
                if value > ((2**maxbits)-1):
                    e.error("Parser","Source constant %d too large (max %d bits available) on line %d " % (value, maxbits, line_no))
        
        return [base, value]
            
    def parser_check_addr(self, str, maxbits):
        # Only recognizes self.symbols and sets alignment at the moment (TODO-?: add constant address + alignment check)
        global symbols
        addr = ''   # empty addr is returned as failure condition
        if str in self.symbols:
            addr = str
            #print self.symbols[addr]
            try:
                self.symbols[addr][self.sf_align]=2 
                self.cmds[self.symbols[addr][self.sf_cmd_no]][self.cf_align] = 2 
            except IndexError:
                e.error("Parser/Prelink", "Failed setting alignment for symbol $str")   
                addr=''
        return [addr]
    
    def link(self):
        """ 
        The linker : 

        1. Sets the addresses so they fit with the alignment
        2. Updates the symbol table with the addresses
        3. Assigns the bit patterns to the opcodes
        """
        
        # Assign and align adddresses
        self.cmds[0][self.cf_addr] = 0x0000 # Base address
        for i in range(1,len(self.cmds)):
            addr = self.cmds[i-1][self.cf_addr] # Start at previous address 
            addr = addr + self.cmds[i][self.cf_align]-(addr%self.cmds[i][self.cf_align]) # Align
            self.cmds[i][self.cf_addr] = addr
        
        # Update the symbol table with addresses
        for key in self.symbols.keys():
            s = self.symbols[key]
            try:
                s.append(self.cmds[s[self.sf_cmd_no]][self.cf_addr])
            except IndexError:
                e.warn("Linker", "Index error for symbol %s" % (key))
        
        ### Create Machine Code (binary)
        
        # Write Opcodes (Sequencer "Machine" binary)
        for i in range(len(self.cmds)):
            self.cmds[i][self.cf_code]=0b110100000000000 # Default is NOOP, no sync, single cycle
            opcode='unsupported'
            regsel=''
            unused=''
            value=''
            c = self.cmds[i]
            tab_code = self.cmds[i][self.cf_opcode]
            if tab_code=='LD':
                opcode = tab_code + c[self.cf_params][0][0] # Add regname to LD
            else:
                opcode = tab_code

            flag_bits_str = self.CodeTable[opcode][1]
            unused = self.CodeTable[opcode][3]
            
            # Set value field
            #if opcode in ['LDCC','LDNC','LDREG','MOVD','SETF','CLF','SDTX','SDTXW',
            if opcode in ['LDREG','MOVD','SETF','CLF','SDTX','SDTXW',
                          'WAIT','NOPC','NOOP','NOOPC','TXVAL','unused0','unused1','unused2','unused3']:
                fmt = "{0:0%db}" % (self.CodeTable[opcode][4])
                value = (fmt).format(int(c[self.cf_params][1][1]))  # Set value field 
            elif opcode in ['LDCC','LDNC']:
                fmt = "{0:0%db}" % (self.CodeTable[opcode][4])
                value = (fmt).format(int(c[self.cf_params][1][1]))  # Set value field 
            
            if flag_bits_str:
                # TODO
                flags = flag_bits_str # copy
                for flag in 'BASK':
                    if flag in flags :
                        if flag in c[self.cf_flags] : 
                            flags = flags.replace(flag,'1', 1)
                        else:
                            flags = flags.replace(flag,'0', 1)
            else:
                flags = ''

            if tab_code=='LD':
                opcode = tab_code + c[self.cf_params][0][0]
                if opcode in ['LDREG']: # Set regsel field 
                    fmt = "{0:0%db}" % (self.CodeTable[opcode][2])
                    regsel = (fmt).format(int(c[self.cf_params][0][1]))
#               if opcode in ['LDREG','LDAR','LDBAR','LDCC']:
#                   flags = ''
            elif tab_code in ['JUMP','JUMPC','JUMPI','LOOP','LOOPR','CALL']:
                opcode = tab_code
                symb_key = c[self.cf_params][0][0]
                # Set address value
                # Note: only 1 in 2 memory locations are addressable in these commands
                dest_addr = self.symbols[symb_key][self.sf_addr] >> 1   # Due to 10 bit address field and 11 bit address 
                fmt = "{0:0%db}" % (self.CodeTable[opcode][4])
                value = (fmt).format(int(dest_addr))
            elif tab_code in ['RETURN']:
                opcode = tab_code
            mcode = self.CodeTable[opcode][0]
            #print " " + opcode + " " + mcode + " s:"+flags+' r:'+regsel+' u:'+unused+' v:'+value
            self.cmds[i][self.cf_code]=int('0b'+mcode+regsel+flags+unused+value, 0)
        
    def parse(self):
        """
        A large method that:

        1. reads lines from infile
        2. grabs fields, put fields in lists 
        3. performs basic syntax checking
        """
        ### Parser 1 : Read lines of infile, grab fields, and put into structured list

        line_no=0
        cmd_no=0            # Keeps track of command number (skipping empty/comment lines and SYNC)
        flags = ''           # Keep track of flags to affect next command which may be on the next line
    
        for line_id, line in self.lines: 
            line_no = line_id + 1       # Keeps track of input text file line number
            line=line.strip()           # Remove whitespace before / after
            if not line:                    # Matches empty line
                continue
            if re.match(r"^#.*",line):      # Matches comment line 
                continue
            line = re.sub(r"(.*)\s+\#.*",r"\1",line)        # Strip any trailing comment
        
            # Look for a symbol marker (@loc_1) on the start of the line
            symbol=re.match(r"^(@\w+):.*",line)
            if symbol:
                if symbol.group(1) in self.symbols.keys():
                    prev_symbol = self.symbols[symbol.group(1)]
                    # print prev_symbol
                    e.error("Parser", "Error: Duplicate symbol %s on lines %d and %d" % (symbol.group(1), prev_symbol[1], line_no) )
                self.symbols[symbol.group(1)] = [cmd_no, line_no, 1]    # 1 = default address word alignment
                line = re.sub(r"^@\w+:\s*(.*)",r"\1",line)      # Strip the symbol marker and trailing space (@here: )
                if line:
                    e.error("Parser", "Error: Failed parsing line %d" % (line_no) )
                    
            # Look for a constant definition ($constname = expression) on the start of the line
            constant=re.match(r"^\$(\w+)\s*=(.*)",line)
            if constant:
                #print constant.group(1)
                #print constant.group(2)
                ckey = constant.group(1).upper()
                if ckey in self.constants.keys():
                    e.error("Parser", "Error: Duplicate constant definiton of %s on line %d" % (ckey, line_no) )
                try:
                    expr = self.replace_var_const(constant.group(2))
                    self.constants[ckey]=eval(expr)
                except:
                    e.fatal("Parser", "Error: Failure evaluating constant expression for %s on line %d" % (ckey, line_no))
                    self.debug_print_constants(sys.stderr)
                line = re.sub(r"^\$\w+\s*=.*",r"",line)     # Strip the symbol marker and trailing space (@here: )
                if line:
                    e.error("Parser", "Error: Failure parsing line %d" % (line_no) )

            if not line:                # Rest of line is empty
                continue
            
            # Strip any whitespace after [{(:+-*/ or before +-*/:)]} characters
            re_paren_trailspace_s = r"(.*)([:*+-/\[\(\{]+)\s+(.*)"
            re_paren_trailspace_r = r"\1\2\3"
            re_paren_leadspace_s = r"(.*)\s+([:*+-/\]\)\}]+)(.*)"
            re_paren_leadspace_r = r"\1\2\3"
            while re.match(re_paren_trailspace_s, line):
                line = re.sub(re_paren_trailspace_s, re_paren_trailspace_r, line)
            while re.match(re_paren_leadspace_s, line):
                line = re.sub(re_paren_leadspace_s, re_paren_leadspace_r, line)
        
            # find command and parameters and put into cmds
            line = line.strip()
            splitline = re.split(r"[,\t\s]+",line)
            if not splitline:
                self.cmds.append([""])
                continue
            else:
                if not ((splitline[0] in self.asm_opcodes.keys()) or (splitline[0] in self.opcode_flags.keys())):
                    e.error("Parser", "Unrecognized Opcode %s at line %d" % (splitline[0], line_no))

                # insert into self.cmds list
                while splitline[0] in self.opcode_flags.keys():
                    flags = flags+self.opcode_flags[splitline[0]]
                    splitline=splitline[1:]

                if len(splitline)==0:
                    continue # only flags on this line (allowed to put flags on a previous line)

                #print ('%3d SL:' + ' '.join(splitline)) % (line_no)
                opco = self.asm_opcodes.get(splitline[0])
                if (opco in ['MOVD', 'NOOP', 'NOOPC', 'SETF', 'CLF', 'SDTX', 'SDTXW', 'WAIT', 'TXVAL', 'unused0', 'unused1', 'unused2','unused3']):
                    self.cmds.append([flags, opco , [[None,None], splitline[1:]], cmd_no, line_no, 1, None, None])
                else:
                    self.cmds.append([flags, opco , splitline[1:], cmd_no, line_no, 1, None, None])
                cmd_no=cmd_no+1
                flags = ''

        ### 2nd part of parsing (syntax-check and evaluate parameters here)
        # TODO: better or stricter syntax check of operands
        for i in range(len(self.cmds)):     # Main loop for parameter syntax checking
            cmd = self.cmds[i][self.cf_opcode]
            line_no = self.cmds[i][self.cf_line_no]
            params = self.cmds[i][self.cf_params]
            if len(params)>2:
                e.error("Parser", "Max 2 operands, but found %d (%s) at line %d" % (len(params), params, line_no) )
            if cmd=="LD":
                if len(params)!=2:
                    e.error("Parser" , "LD requires two arguments, but found %d (%s). At line %d" % (len(params), params, line_no) )
                op1 = self.parser_regcheck(params[0])
                if not op1[0]:
                    e.error("Parser" , "Unrecognized destination register for LD. Found %s on line %d" % (params[0], line_no) )
                else:
                    self.cmds[i][self.cf_params][0] = op1
                if params[0][0] in ['CC','NC']:
                    op2 = self.parser_srccheck(params[1],['const'],12,line_no) # 12 bits
                else:
                    op2 = self.parser_srccheck(params[1],['const'],8,line_no)  # 8 bits
                if not op2[0]:
                    e.error("Parser" , "Unrecognized source specification for LD. Found %s on line %d" % (params[1], line_no) )
                else:
                    self.cmds[i][self.cf_params][1] = op2
#               if params[0][0]=='REG' and self.cmds[i][self.cf_flags]=='S':
#                   e.warn("Parser" , "SYNC not allowed for LD REG, ignored on line %d" % ( line_no) )
            elif cmd in ['JUMP', 'JUMPC', 'JUMPI', 'CALL', 'LOOPR', 'LOOP']:
                if len(params)!=1:
                    e.error("Parser" , cmd+ " requires 1 argument, but found %d (%s). At line %d" % (len(params), params, line_no) )
                op1 = self.parser_check_addr(params[0], maxbits=10)
                if not op1[0]:
                    e.error("Parser" , "Undeterminable destination address for JUMP*/CALL/LOOP*. Found %s on line %d" % (params[0], line_no) )
                else:
                    self.cmds[i][self.cf_params][0] = op1
            elif cmd in ['MOVD', 'SETF', 'CLF','SDTX','SDTXW','WAIT','TXVAL','unused0','unused1','unused2','unused3']: # 1 argument
                if len(params)!=2:
                    e.error("Parser" , cmd+" requires 1 argument, but found %d (%s). At line %d" % (len(params)-1, params, line_no) )
#               if cmd=='MOVV':
#                   #print params[1]
#                   op2 = self.parser_srccheck(params[1][0],['VM','const'],8,line_no)
                if cmd in ['MOVD', 'SETF','CLF','SDTX','SDTXW','WAIT','TXVAL','unused0','unused1','unused2'] :
                    op2 = self.parser_srccheck(params[1][0],['const'],8,line_no)
                elif cmd in ['unused3']:
                    op2 = self.parser_srccheck(params[1][0],['const'],11,line_no)
                if not op2[0]:
                    e.error("Parser" , "Unrecognized source specification for LD. Found %s on line %d" % (params[1], line_no) )
                else:
                    #print(op2)
                    self.cmds[i][self.cf_params][1] = op2
            elif cmd in ['NOOP','NOOPC']: # 1 optional argument
                if len(params[1])>1:
                    e.error("Parser" , cmd+" has 1 optional argument, but found %d (%s). At line %d" % (len(params)-1, params, line_no) )
                elif len(params[1])<1:
                    params[1]=['0']
                op2 = self.parser_srccheck(params[1][0],['const'],8,line_no)
                if not op2[0]:
                    e.error("Parser" , "Unrecognized source specification for LD. Found %s on line %d" % (params[1], line_no) )
                else:
                    self.cmds[i][self.cf_params][1] = op2
            elif cmd in ['TXTEMP','TXBR','LDTEMP','MOVTEMP']: # 0 arguments
                #print cmd, params
                if len(params)>0:
                    e.error("Parser" , cmd+" has no arguments, but found %d (%s). At line %d" % (len(params)-1, params, line_no) )
                self.cmds[i][self.cf_params] = [[None, None], None]


        ## Quit if errors :

        if e.errors>0:
            print(f"Exit with {e.errors} errors in {sys.argv[-1]}")
            sys.exit(1)



    ### Output procedures 
    def debug_print_constants(self, f):
        """
        Writes the evaluated constants to f (typically stdout or stderr), for the purpose of debugging.
        """
        f.write( "Constants Table = {\n" )
        for key, value in sorted(self.constants.items()):
            f.write( "    " + key + " : " + str(value) + "\n") 
        f.write( "}\n" )

    def debug_print_cmds(self, f):      
        """
        Writes the contents of the commands table to f (typically stdout or stderr), for the purpose of debugging.
        """
        # Useful method for debug of this script, but not intended for production
        f.write( "%4s "   % 'FLAG' )      # Sync field
        f.write( "%7s "   % 'OPCODE' )        # Opcode field
        f.write( "%35s "  % 'DESTINATION' )  # Parameter array field
        f.write( "%15s "  % 'SOURCE' )   # Parameter array field
        f.write( "%6s "   % 'CMD_NO' )        # Cmd_no
        f.write( "%7s "   % 'LINE_NO' )       # Line_no
        f.write( "%5s "   % 'ALIGN' )     # Line_no
        f.write( "%7s "   % 'ADDRESS' )       # Line_no
        f.write( "%15s\n" % "Binary code" )     # Line_no
        for c in self.cmds:
            flags='BASK'
            for flag in flags:
                if not flag in c[0]:
                    flags=flags.replace(flag,' ')
            f.write( "%4s " % flags )        # Sync field
            f.write( "%7s " % c[1] )        # Opcode field
            if len(c[self.cf_params])==0:
                f.write( "%35s " % '-' )    
                f.write( "%15s " % '-' )    
            elif len(c[self.cf_params])==1:
                f.write( "%35s " % c[self.cf_params][0] )   
                f.write( "%15s " % '-' )    
            elif len(c[self.cf_params])==2:
                f.write( "%35s " % c[self.cf_params][0] )   
                f.write( "%15s " % c[self.cf_params][1] )   
            f.write( "%6s "  % c[3] )       # Cmd_no
            f.write( "%7s " % c[4] )        # Line_no
            f.write( "%5s " % c[self.cf_align] )        # Alignment
            f.write( "%7s " % c[self.cf_addr] )     # Alignment
            f.write( '{0:015b}'.format(c[self.cf_code]) )       # Alignment
            f.write("\n")

    def write_symbol_table(self, f):
        """
        Writes a table of symbols, address, line number and address alignment, to the file f.
        """
        f.write("%35s " % "Symbol")
        f.write("%10s " % "CMD_NO")
        f.write("%10s " % "LINE_NO")
        f.write("%10s " % "ALIGNMENT") 
        f.write("\n") 
        
        sort_on_symbol_name = "lambda x: x[0]"
        sort_on_cmd_line_no = "lambda x: x[1]"
        
        for v in sorted(self.symbols.items(), key=eval(sort_on_cmd_line_no)):
            f.write("%35s " % v[0])
            for sv in v[1] :
                f.write("%10s " % sv)
            f.write("\n")
    
    def write_symbol_parfile(self, f):
        """
        Writes to the file f from the table of symbols (without the ``@`` character):

          parameter addr_<symbol_name>_c = address in instr mem

        Example output :
        
        .. code-block:: c

            parameter addr_f_set_user_irq_0_c = 41;
            parameter addr_f_set_user_irq_1_c = 44;
            parameter addr_f_set_user_irq_2_c = 47;
        """

        f.write("// Verilog parameter table include file for symbols (purpose: verification)\n")
        
        sort_on_symbol_name = "lambda x: x[0]"
        sort_on_cmd_line_no = "lambda x: x[1]"
        
        for v in sorted(self.symbols.items(), key=eval(sort_on_cmd_line_no)):
            f.write("parameter addr_%s_c = %d;\n" % (v[0][1:],v[1][self.sf_addr]))
    
    def write_mco(self, f, fill=1, fill_value=0b111000000000000, format_str="{0:015b} // 0x{1:04X}h {2}\n"):
        """
         Writes machine code binary (string) output

         format_str fields:

            0 - intruction code
            1 - address
            2 - opcode (text) / 'fill' if filling 

         Examples:
         
            .. code-block:: python

                format_str="{0:015b} // Addr: 0x{1:04X}h {2}\\n"

            output: 

                101000100001010 // Addr: 0x0000h LD

            .. code-block:: python

                format_str="{1},{0}\\n"

            outputs csv-style address, instruction in decimal

            .. code-block:: python
    
                format_str="i_spi_master.tk_bus_write_16((addr_instr_mem_min_c+(2*{1})),  15'b{0:0.15b},0,0); // {1} {2} \\n"

            outputs verilog testbench task commands as in the predefined format
        
        """
        last_addr = 0
        for c in self.cmds:
            while c[self.cf_addr]>last_addr:
                if fill==1:
                    f.write(format_str.format(fill_value, last_addr, 'fill'))
                last_addr = last_addr + 1
            f.write(format_str.format(c[self.cf_code], last_addr, c[self.cf_opcode]))
            last_addr = last_addr + 1
         
    def write_mco_8b_testbench(self, f, fill=1):
        # Does the same thing as write_mco, but tailored to the input needs of the Testbench software used during validation.
        iram_base_addr = 8192
        last_addr = 0
        prog_list_int=[]
        for c in self.cmds:
            while c[self.cf_addr]>last_addr:
                if fill==1:
                    # f.write("0x{0:04X},0x{1:04X},\n".format(0, 114, (iram_base_addr+2*last_addr), 'fill'))
                    f.write("{0:015b} // 0x{1:04X}h {2}\n".format(29184, last_addr, 'fill'))
                    prog_list_int.append(lsb)
                    prog_list_int.append(msb)
                last_addr = last_addr + 1
            
            n = c[self.cf_code] 
            msb= n>>8
            lsb= n & 255
            # f.write("0x{0:04X},0x{1:04X},\n".format(lsb, msb, (iram_base_addr+2*last_addr), c[self.cf_opcode]))
            f.write("{0:015b} // 0x{1:04X}h {2}\n".format(c[self.cf_code], last_addr, c[self.cf_opcode]))
            prog_list_int.append(lsb)
            prog_list_int.append(msb)            
            last_addr = last_addr + 1
        return prog_list_int
        
    def get_cmds_list(self):
        """Returns the list of commands"""
        return list(c[self.cf_code] for c in self.cmds)
    
    def get_addr_list(self):
        """Returns the list of memory addresses for the commands"""
        return list(c[self.cf_addr] for c in self.cmds)
    
    ### Disassembler ( for internal software verification purpose )
    # Uses CodeTable and binary string mainly to decode the instruction into human readable list item.

    def disasm_simple(self, cmds):  
        """
        A simple disassembler for the purpose of test & verification of this class.

        Note: Need to call this prior to simulation as simulator uses dCode.
        """
        # cmds - integer list of [addr, instruction]
        if self.debug:
            print("*** disasm start ***")
        dCode=[]
        for c in cmds:
            dec_code = c
            bin_code = "{0:015b}".format(dec_code)

            code_d = [0,0,0,0,0,0]

            # Acquire in code_t correct CodeTable item in list form :

            if bin_code[0:3] == "000":
                code_t = ['LDCC', list(self.CodeTable["LDCC"])]
            elif bin_code[0:3] == "001":
                code_t = ['LDNC', list(self.CodeTable["LDNC"])]
            elif bin_code[0:5] == "01000":
                code_t = ['CALL', list(self.CodeTable["CALL"])]
            elif bin_code[0:5] == "01001":
                code_t = ['JUMP', list(self.CodeTable["JUMP"])]
            elif bin_code[0:5] == "01010":
                code_t = ['JUMPC', list(self.CodeTable["JUMPC"])]
            elif bin_code[0:5] == "01011":
                code_t = ['JUMPI', list(self.CodeTable["JUMPI"])]
            elif bin_code[0:5] == "01100":
                code_t = ['LOOP', list(self.CodeTable["LOOP"])]
            elif bin_code[0:5] == "01101":
                code_t = ['LOOPR', list(self.CodeTable["LOOPR"])]
            elif bin_code[0:7] == "0111000":
                code_t = ['RETURN', list(self.CodeTable["RETURN"])]
            elif bin_code[0:7] == "0111001":
                code_t = ['unused0', list(self.CodeTable["unused0"])]
            elif bin_code[0:7] == "0111010":
                code_t = ['SETF', list(self.CodeTable["SETF"])]
            elif bin_code[0:7] == "0111011":
                code_t = ['CLF', list(self.CodeTable["CLF"])]
            elif bin_code[0:7] == "0111100":
                code_t = ['SDTX', list(self.CodeTable["SDTX"])]
            elif bin_code[0:7] == "0111101":
                code_t = ['SDTXW', list(self.CodeTable["SDTXW"])]
            elif bin_code[0:7] == "0111110":
                code_t = ['unused1', list(self.CodeTable["unused1"])]
            elif bin_code[0:7] == "0111111":
                code_t = ['WAIT', list(self.CodeTable["WAIT"])]
            elif bin_code[0:2] == "10":
                code_t = ['LDREG', list(self.CodeTable["LDREG"])]
            elif bin_code[0:4] == "1100":
                code_t = ['MOVD', list(self.CodeTable["MOVD"])]
            elif bin_code[0:4] == "1101":
                code_t = ['NOOPC', list(self.CodeTable["NOOPC"])]
            elif bin_code[0:6] == "111000":
                code_t = ['TXVAL', list(self.CodeTable["TXVAL"])]
            elif bin_code[0:6] == "111001":
                code_t = ['TXTEMP', list(self.CodeTable["TXTEMP"])]
            elif bin_code[0:6] == "111010":
                code_t = ['LDTEMP', list(self.CodeTable["LDTEMP"])]
            elif bin_code[0:6] == "111011":
                code_t = ['TXBR', list(self.CodeTable["TXBR"])]
            elif bin_code[0:6] == "111100":
                code_t = ['MOVTEMP', list(self.CodeTable["MOVTEMP"])]
            elif bin_code[0:6] == "111101":
                code_t = ['unused2', list(self.CodeTable["unused2"])]
            elif bin_code[0:5] == "11111":
                code_t = ['unused3', list(self.CodeTable["unused3"])]
            else:
                print(bin_code)
                print("Fatal: Unrecognized machine code : " + str(bin_code))
                print("This error message is due to a software bug, not the input file.")
                sys.exit(1)
            
            # Populate / set field values in code_t, code_d, based on bin_code :
            code_d[0] = eval("0b%s" % code_t[1][0])

            bitid = len(code_t[1][0])   # Set to end of code (=start of regsel or next if no regsel)

            ## Regsel
            if code_t[1][2] > 0 :   # Take regsel
                rsl = code_t[1][2]
#                print bin_code[bitid:bitid+rsl]
                code_d[1]=eval("0b"+bin_code[bitid:bitid+rsl])
                code_t[1][2] = "rs="+str(code_d[2])
                bitid = bitid+rsl

            ## Sync bit
            if code_t[1][1]:         # Get flags bits #TODO new flags
                sbits = code_t[1][1]
                code_t[1][1] = "S='%s'" % bin_code[bitid:bitid+len(sbits)]
#                print code_t[1][1]
                code_d[2] = eval('0b'+bin_code[bitid:bitid+len(sbits)])
                bitid = bitid + len(sbits)
            else: # Get none flags bit ''
                code_t[1][1] = "S=''"
                code_d[2]=0

            ## Unused bits
            bitid2 = bitid + len(code_t[1][3])
            code_t[1][3] = 'u="%s"' % bin_code[bitid:bitid2]
            if bitid2>bitid:
                code_d[3] = eval("0b"+bin_code[bitid:bitid2])
            bitid = bitid2

            ## Value (immediate)
            valstr = bin_code[bitid:bitid+code_t[1][4]]
            #print bitid, code_t[1][4], bin_code[bitid:bitid+code_t[1][4]]
            
            try:
                if (valstr): 
                    code_d[4] = eval("0b"+valstr)
                    code_t[1][4] = "val=%d" % code_d[4]
                else:
                    code_d[4] = 0           
                    code_t[1][4] = "val=''"
            except SyntaxError:
                print(valstr)
                print("SyntaxError when evaluating machine code immediate value.")
                sys.exit(1)
            
            code_d[5]=dec_code
            # TODO : Could check equivalence here (except address?)
            if self.debug:
                print(bin_code[0:4], code_t)
        
            dCode.append([code_t[0], code_d])
        self.dCode = dCode
        if self.debug:
            print("*** disasm stop ****")
            print("\ndCode table:")
            for d in dCode:
                print(d)
    
