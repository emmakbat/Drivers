import numpy as np
from numpy import matmul as mul
from numpy.linalg import inv as inv
from numpy.linalg import eig as eig
from numpy import tensordot as tensor
from numpy import dot
import pickle

import itertools
import sequence_rb
from gates import Gate


# list of Paulis in string representation
list_sSign = ['+','-'] # 
list_sPauli = ['I','X','Y','Z']
list_s2QBPauli = list(itertools.product(list_sSign,list_sPauli, list_sPauli))

# list of Paulis, 1QB-gates, and 2QB-gates in np.matrix representation
dict_mPauli = {'I': np.matrix('1,0;0,1'), 
    'X': np.matrix('0,1;1,0'),
    'Y': np.matrix('0,-1j;1j,0'),
    'Z': np.matrix('1,0;0,-1')}

dict_m1QBGate = {'I': np.matrix('1,0;0,1'),
    'X2p': 1/np.sqrt(2)*np.matrix('1,-1j;-1j,1'), 
    'X2m': 1/np.sqrt(2)*np.matrix('1,1j;1j,1'),
    'Y2p': 1/np.sqrt(2)*np.matrix('1,-1;1,1'),
    'Y2m': 1/np.sqrt(2)*np.matrix('1,1;-1,1'),
    'Z2p': np.matrix('1,0;0,1j'),
    'Z2m': np.matrix('1,0;0,-1j'),
    'Xp': np.matrix('0,1j;1j,0'),
    'Xm': np.matrix('0,-1j;-1j,0'),
    'Yp': np.matrix('0,-1;1,0'),
    'Ym': np.matrix('0,1;-1,0'),
    'Zp': np.matrix('1,0;0,-1'),
    'Zm': np.matrix('1,0;0,-1')
    }
dict_m2QBGate = {'SWAP': np.matrix('1,0,0,0; 0,0,1,0; 0,1,0,0; 0,0,0,1'),
    'CZ': np.matrix('1,0,0,0; 0,1,0,0; 0,0,1,0; 0,0,0,-1'),
    'iSWAP': np.matrix('1,0,0,0; 0,0,1j,0; 0,1j,0,0; 0,0,0,1'),
    'CNOT': np.matrix('1,0,0,0; 0,1,0,0; 0,0,0,1; 0,0,1,0')}


def expect(_psi, _op):
    """
    Get the expectation value of the operator, given the quantum state 
    
    Parameters
    ----------
    _psi: np.matrix 
        the state vector of a quantum state
    _op: np.matrix
        a quantum operator 
    
    Returns
    -------
    e_val: expectation value
    """
    return dot(_psi.H, dot(_op, _psi))[0,0]

def sPauli_to_mPauli(_sPaulis):
    """
    Convert from string-type Paulis to matrix-type Paulis 
    
    Parameters
    ----------
    _sPaulis: string
        string representation of a quantum state
    _op: np.matrix
        quantum operator 
    
    Returns
    -------
    e_val: expectation value
    """
    sign = _sPaulis[0]
    dim = len(_sPaulis) - 1
    _mPaulis = np.matrix([1])
    for i in range(1,len(_sPaulis)):
        if _sPaulis[i] == 'I':
            _mPaulis = np.kron(_mPaulis, dict_mPauli['I'])
        elif _sPaulis[i] == 'X':
            _mPaulis = np.kron(_mPaulis, dict_mPauli['X'])
        elif _sPaulis[i] == 'Y':
            _mPaulis = np.kron(_mPaulis, dict_mPauli['Y'])
        elif _sPaulis[i] == 'Z':
            _mPaulis = np.kron(_mPaulis, dict_mPauli['Z'])

    if sign == '+':
        return _mPaulis
    else:
        return -1.0 * _mPaulis

def Gate_to_strGate(_Gate):
    """
    represent Gate (defined in "gates.py") object in string-format.
    
    Parameters
    ----------
    Gate: gates.Gate
        Gate object
    
    Returns
    -------
    str_Gate: string
        string representation of the Gate
    """
    if (_Gate == Gate.I):
        str_Gate = 'I'
    elif (_Gate == Gate.Xp):
        str_Gate = 'Xp'
    elif (_Gate == Gate.Xm):
        str_Gate = 'Xm'
    elif (_Gate == Gate.X2p):
        str_Gate = 'X2p'
    elif (_Gate == Gate.X2m):
        str_Gate = 'X2m'
    elif (_Gate == Gate.Yp):
        str_Gate = 'Yp'
    elif (_Gate == Gate.Ym):
        str_Gate = 'Ym'
    elif (_Gate == Gate.Y2p):
        str_Gate = 'Y2p'
    elif (_Gate == Gate.Y2m):
        str_Gate = 'Y2m'
    elif (_Gate == Gate.Zp):
        str_Gate = 'Zp'
    elif (_Gate == Gate.Zm):
        str_Gate = 'Zm'
    elif (_Gate == Gate.Z2p):
        str_Gate = 'Z2p'
    elif (_Gate == Gate.Z2m):
        str_Gate = 'Z2m'
    elif (_Gate == Gate.CZ):
        str_Gate = 'CZ'

    return str_Gate


def strGate_to_Gate(_strGate):
    """
    Convert from string-type Gates to Gate (defined in "gates.py") object 
    
    Parameters
    ----------
    str_Gate: string
        string representation of the Gate
    
    Returns
    -------
    Gate: gates.Gate
        Gate object
    """
    if (_strGate == 'I'):
        g = Gate.I
    elif (_strGate == 'Xp'):
        g = Gate.Xp
    elif (_strGate == 'Xm'):
        g = Gate.Xm
    elif (_strGate == 'X2p'):
        g = Gate.X2p
    elif (_strGate == 'X2m'):
        g = Gate.X2m
    elif (_strGate == 'Yp'):
        g = Gate.Yp
    elif (_strGate == 'Ym'):
        g = Gate.Ym
    elif (_strGate == 'Y2p'):
        g = Gate.Y2p
    elif (_strGate == 'Y2m'):
        g = Gate.Y2m
    elif (_strGate == 'Zp'):
        g = Gate.Zp
    elif (_strGate == 'Zm'):
        g = Gate.Zm
    elif (_strGate == 'Z2p'):
        g = Gate.Z2p
    elif (_strGate == 'Z2m'):
        g = Gate.Z2m
    elif (_strGate == 'CZ'):
        g = Gate.CZ

    return g

def get_stabilizer(_psi):
    """
    Get the stabilizer group corresponding the qubit_state
    
    Parameters
    ----------
    _psi: np.matrix
        The state vector of the qubit.
    Returns
    -------
    stabilizer: list 
        The stabilizer group
    """
    stabilizer = []
    for _sPauli in list_s2QBPauli:
        _mPauli = sPauli_to_mPauli(_sPauli)
        _identity = np.identity(_mPauli.shape[0], dtype = complex)
        # if (np.abs(expect(_psi, _mPauli - _identity) - 0) < 1e-1): # check whether _mPauli is the stabilizer.
        if (np.abs(expect(_psi, _mPauli ) - 1) < 1e-6): # check whether _mPauli is the stabilizer.
            stabilizer.append(_sPauli)

    return stabilizer

def generate_2QB_Cliffords(_index):
    seq_QB1 = []
    seq_QB2 = []
    sequence_rb.add_twoQ_clifford(_index, seq_QB1, seq_QB2)
    m2QBClifford = np.identity(4, dtype = complex)
    for i in range(len(seq_QB1)):
        _mGate = np.matrix([1])
        if (seq_QB1[i] == Gate.CZ or seq_QB2[i] == Gate.CZ ): # two qubit gates
            _mGate = np.kron(dict_m2QBGate['CZ'], _mGate)
        else: # 1QB gates
            for g in [seq_QB2[i], seq_QB1[i]]:
                if (g == Gate.I):
                    _mGate = np.kron(dict_m1QBGate['I'], _mGate)
                elif (g == Gate.Xp):
                    _mGate = np.kron(dict_m1QBGate['Xp'], _mGate)
                elif (g == Gate.Xm):
                    _mGate = np.kron(dict_m1QBGate['Xm'], _mGate)
                elif (g == Gate.X2p):
                    _mGate = np.kron(dict_m1QBGate['X2p'], _mGate)
                elif (g == Gate.X2m):
                    _mGate = np.kron(dict_m1QBGate['X2m'], _mGate)
                elif (g == Gate.Yp):
                    _mGate = np.kron(dict_m1QBGate['Yp'], _mGate)
                elif (g == Gate.Ym):
                    _mGate = np.kron(dict_m1QBGate['Ym'], _mGate)
                elif (g == Gate.Y2p):
                    _mGate = np.kron(dict_m1QBGate['Y2p'], _mGate)
                elif (g == Gate.Y2m):
                    _mGate = np.kron(dict_m1QBGate['Y2m'], _mGate)
                elif (g == Gate.Zp):
                    _mGate = np.kron(dict_m1QBGate['Zp'], _mGate)
                elif (g == Gate.Zm):
                    _mGate = np.kron(dict_m1QBGate['Zm'], _mGate)
                elif (g == Gate.Z2p):
                    _mGate = np.kron(dict_m1QBGate['Z2p'], _mGate)
                elif (g == Gate.Z2m):
                    _mGate = np.kron(dict_m1QBGate['Z2m'], _mGate)

        m2QBClifford = mul(_mGate, m2QBClifford)
    return (m2QBClifford)

def saveData(file_path, data):

    """
    Create a log file. (Use the built-in pickle module)
    
    Parameters
    ----------
    file_path: str 
        path of the log file

    - data: arbitrary object
        arbitrary Python object which contains data

    Returns
    -------
    """

    with open(file_path, 'wb') as _output:
        pickle.dump(data, _output, pickle.HIGHEST_PROTOCOL)
    print('--- File Save Success! ---')
    print(file_path)

def loadData(file_path):

    """
    Load a log file. (Use the built-in pickle module)
    
    Parameters
    ----------
    file_path: str 
        path of the log file


    Returns
    -------
    - data: arbitrary object
        arbitrary Python object which contains data
    """

    with open(file_path, 'rb') as _input:
        data = pickle.load(_input)
    print('--- File Load Success! --- ')
    print(file_path)
    return data
    
# if __name__ == "__main__":
    # -------------------------------------------------------------------
    # ----- THIS IS FOR GENERATING RECOVERY CLIFFORD LOOK-UP TABLE ------
    # -------------------------------------------------------------------

    # Start with ground state
    psi_gnd = np.matrix('1;0;0;0')
    
    N_2QBcliffords = 11520
    list_stabilizer = []
    list_psi = []
    list_recovery_gates_QB1 = []
    list_recovery_gates_QB2 = []
    cnt = 0

    # Apply 11520 different 2QB cliffords and get the corresponding stabilizer states
    for i in range(N_2QBcliffords):
        if (i/N_2QBcliffords > cnt):    
            print('Running... %d %%'%(cnt*100))
            cnt = cnt+0.01
        g = generate_2QB_Cliffords(i)
        psi = dot(g, psi_gnd)
        stabilizer = get_stabilizer(psi)  

        # append only if the state is not in list_stablizier list. 
        if (not (stabilizer in list_stabilizer)):
            list_stabilizer.append(stabilizer)
            list_psi.append(psi)
            # find the cheapest recovery clifford gate.
            print('stabilizer state: '+ str(stabilizer))
            print('psi: ' + str(psi.flatten()))
            print('find the cheapest recovery clifford gate')
            min_N_2QB_gate = np.inf
            min_N_1QB_gate = np.inf
            max_N_I_gate = -np.inf
            cheapest_index = None
            # cheapest_recovery_seq_QB1 = []
            # cheapest_recovery_seq_QB2 = []

            for j in range(N_2QBcliffords):
                recovery_gate = generate_2QB_Cliffords(j)
                seq_QB1 = []
                seq_QB2 = []
                sequence_rb.add_twoQ_clifford(j, seq_QB1, seq_QB2)

                if np.abs(1-np.abs(dot(recovery_gate, psi)[0,0])) < 1e-6: # if the gate is recovery, check if it is the cheapest.
                    # Less 2QB Gates, Less 1QB Gates, and More I Gates = the cheapest gate.
                    # The priority: less 2QB gates > less 1QB gates > more I gates
                    N_2QB_gate = 0
                    N_1QB_gate = 0
                    N_I_gate = 0

                    # count the numbers of the gates
                    for k in range(len(seq_QB1)):
                        if (seq_QB1[k] == Gate.CZ or seq_QB2[k] == Gate.CZ):
                            N_2QB_gate += 1
                        else:
                            N_1QB_gate += 2
                        if (seq_QB1[k] == Gate.I):
                            N_I_gate += 1
                        if (seq_QB2[k] == Gate.I):
                            N_I_gate += 1

                    # check whether it is the cheapest
                    if (N_2QB_gate < min_N_2QB_gate): # less 2QB gates
                        if (N_1QB_gate < min_N_1QB_gate): # less 1QB gates
                            if (N_I_gate > max_N_I_gate): # more I gates
                                min_N_2QB_gate = N_2QB_gate
                                min_N_1QB_gate = N_1QB_gate
                                max_N_I_gate = N_I_gate
                                cheapest_index = j
                                # cheapest_recovery_seq_QB1 = seq_QB1
                                # cheapest_recovery_seq_QB2 = seq_QB2

            seq_recovery_QB1 = []
            seq_recovery_QB2 = []
            sequence_rb.add_twoQ_clifford(cheapest_index, seq_recovery_QB1, seq_recovery_QB2)

            # remove redundant Identity gates
            index_identity = [] # find where identity gates are
            for p in range(len(seq_recovery_QB1)):
                if (seq_recovery_QB1[p] == Gate.I and seq_recovery_QB2[p] == Gate.I):
                    index_identity.append(p)
            seq_recovery_QB1 = [m for n, m in enumerate(seq_recovery_QB1) if n not in index_identity]
            seq_recovery_QB2 = [m for n, m in enumerate(seq_recovery_QB2) if n not in index_identity]

            # convert the sequences into the text-format (Avoid using customized python class objects)
            for _seq in [seq_recovery_QB1, seq_recovery_QB2]:
                for q in range(len(_seq)):
                    _seq[q] = Gate_to_strGate(_seq[q])
            list_recovery_gates_QB1.append(seq_recovery_QB1)
            list_recovery_gates_QB2.append(seq_recovery_QB2)
            print('The cheapest recovery clifford gate (QB1): ' + str(seq_recovery_QB1))
            print('The cheapest recovery clifford gate (QB2): ' + str(seq_recovery_QB2))
            print('\n')

    # save the results.
    dict_result ={}
    dict_result['psi_stabilizer'] = list_stabilizer
    dict_result['psi'] = list_psi
    dict_result['recovery_gates_QB1'] = list_recovery_gates_QB1
    dict_result['recovery_gates_QB2'] = list_recovery_gates_QB2
    saveData_pickle('recovery_rb_table.pickle', dict_result)
    
    # load the results.
    # dict_result =loadData_dill('recovery_rb_table.dill')
    # print(dict_result['psi_stabilizer'])
