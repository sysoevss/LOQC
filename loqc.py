from math import pi, sqrt
import numpy as np
import numpy.linalg as la
#from scipy.linalg import sqrtm
from functools import reduce
from sympy import expand, sympify, latex, Float
import json
import data
from re import sub

#
#  Function declarations
#
def BS(theta, phi, mode1, mode2, dim):
    res = np.identity(dim, dtype = 'complex_')
    res[mode1][mode1] = np.cos(theta)
    res[mode1][mode2] = -np.exp(1j*phi) * np.sin(theta)
    res[mode2][mode1] = np.exp(-1j*phi) * np.sin(theta)
    res[mode2][mode2] = np.cos(theta)
    return res
def PS(phi, mode, dim):
    res = np.identity(dim, dtype = 'complex_')
    res[mode][mode] = np.exp(1j*phi) 
    return res

def run_circuit(input, matrix, dim):
    for i in range(dim):
        if "a" + str(i+1) in input:
            b_repr = "("
            for j in range(dim):
                b_repr += "+(" + str(matrix[i][j]) + ")*b" + str(j+1)
            b_repr += ")"
            input = input.replace("a" + str(i+1), b_repr)
    # paired outputs
    res = str(expand(input))
    for mode in range(1, dim + 1):
        res = res.replace("b" + str(mode) + "**2", str(sqrt(2)) + "*b" + str(mode) + "**2")
        res = res.replace("b" + str(mode) + "**3", str(sqrt(6)) + "*b" + str(mode) + "**3")
        res = res.replace("b" + str(mode) + "**4", str(sqrt(24)) + "*b" + str(mode) + "**4")
        res = res.replace("b" + str(mode) + "**5", str(sqrt(120)) + "*b" + str(mode) + "**5")
        res = res.replace("b" + str(mode) + "**6", str(sqrt(720)) + "*b" + str(mode) + "**6")
        res = res.replace("b" + str(mode) + "**7", str(sqrt(8040)) + "*b" + str(mode) + "**7")
    return expand(res)

def use_result(input, mode, val):
    mode_name = "b" + str(mode)
    if val == 0:
        values = {mode_name: 0}
        input = sympify(input).subs(values)
    if val == 1:
        # dealing with terms having no mode-x
        values2 = {mode_name: 0}
        expr = input.subs(values2)
        input = expand(input - expr)
        # dealing with terms having more than 1 mode-x
        expr2 = expand(input / sympify(mode_name))
        expr2 = expr2.subs(values2)
        input = expr2 
    return input

def sub_circ(matrix, dim, modes):
    res = np.identity(dim, dtype = 'complex_')
    circ_dim = len(modes)
    for i in range(circ_dim):
        for j in range(circ_dim):
            res[modes[i]][modes[j]] = matrix[i][j]
    return res

def print_result(input):    
    init_printing()
    return expand(input.xreplace(dict([(n,0) for n in input.atoms(Float) if abs(n) < 1e-12])))  

def ConstructCircuit(devs, modes): 
    circuit = []
    circuit.append(np.identity(modes, dtype = 'complex_'))
    input = "1"

    # process inputs
    inputs = [a for a in devs if a['type'] == "IN"]   
    for d in inputs:
        if d['n'] != "-":
            n = int(d['n'])
            mode = d['modes'][0]['mode'] + 1
            if n > 0:
                input += " * a" + str(mode)
                for i in range(n - 1):
                    input += "*a" + str(mode)
    # process devices
    devices = [a for a in devs if (a['type'] != "IN" and a['type'] != "OUT")]   
    devs_sorted = sorted(devices, reverse = True, key=lambda d: d['step']) 
    for d in devs_sorted:
        if d['type'] == "PS":
            circuit.append(PS(np.radians(float(d['phi'])), d['modes'][0]['mode'], modes))
        if d['type'] == "BS":
            mode1 = -1
            mode2 = -1
            for m in d['modes']:
                if m['my_port'] == "hybrid0":
                    mode1 = m['mode']
                if m['my_port'] == "hybrid2":
                    mode2 = m['mode']
            circuit.append(BS(np.radians(float(d['theta'])), np.radians(float(d['phi'])), mode1, mode2, modes))
        if d['type'] == "User Project":
            circ = data.GetCircuit(d['project_key'])
            matr_string = circ.matrix.replace("\n", "").replace(" ", "").replace("[", "").replace("]]", "").replace("]", ";").replace("&", " ")
            #return matr_string, np.identity(1)            
            circ_m = np.asarray(np.matrix(str(matr_string)))
            circ_modes = [-1 for i in range(circ.modes)]
            for m in d['modes']:
                index = int(m['my_port'][6:]) / 2
                circ_modes[index] = m['mode']
            circuit.append(sub_circ(circ_m, modes, circ_modes))

    # RUN!
    matrix = reduce(np.dot, circuit)
    inv = la.inv(matrix)
    input = run_circuit(input, inv, modes)

    # process outputs
    outputs = [a for a in devs if a['type'] == "OUT"]   
    for d in outputs:
        if d['n'] != "-":
            n = int(d['n'])
            mode = d['modes'][0]['mode'] + 1
            if n >= 0:
                input = use_result(input, mode, n)

    result = latex(expand(input.xreplace(dict([(n,0) for n in input.atoms(Float) if abs(n) < 1e-12]))))
    return result, np.array2string(matrix, separator='&'), np.array2string(inv, separator='&')


#
#  Fidelity & Probability part
#

def getCircuitFidelityData(project_key, bs_error):
    try:
        # check
        proj = data.Project.get(project_key)
        if not proj:
            return None, "No project"

        # get matrices
        devs, modes, error = data.getDevsModes(proj)
        matrix, inv, error = ConstructCircuitMatrixWithError(devs, modes, bs_error)
        if error:
            return None, error

        # get modes utilisation
        control_modes = []
        dest_modes = []
        ancilla_in_ones = []
        ancilla_out_ones = []
        ancilla_zeros = []
        ancillas = []
        # inputs
        for d in devs:
            if d['type'] == "IN":
                mode = d['modes'][0]['mode'] + 1
                if d['input_type'] == "0":
                    dest_modes.append(mode)
                if d['input_type'] == "1":
                    ancillas.append(mode)
                    if d['n'] == "1":
                        ancilla_in_ones.append(mode)
                if d['input_type'] == "2":
                    control_modes.append(mode)
        control_modes = sorted(control_modes)
        dest_modes = sorted(dest_modes)
        # outputs 
        for d in devs:
            if d['type'] == "OUT":
                mode = d['modes'][0]['mode'] + 1
                if mode in ancillas:
                    if d['n'] == "1":
                        ancilla_out_ones.append(mode)
                    if d['n'] == "0":
                        ancilla_zeros.append(mode)

        return {"matrix": inv, 
                "control_modes": control_modes, 
                "dest_modes": dest_modes, 
                "ancilla_in_ones": ancilla_in_ones, 
                "ancilla_out_ones": ancilla_out_ones, 
                "ancilla_zeros": ancilla_zeros,
                "modes": modes}, ""
    except Exception as ex:
        return None, "getCircuitFidelityData: " + str(ex)      

def ConstructCircuitMatrixWithError(devs, modes, bs_error):
    try:
        # prepare
        circuit = []
        circuit.append(np.identity(modes, dtype = 'complex_'))

        # process devices
        devices = [a for a in devs if (a['type'] != "IN" and a['type'] != "OUT")]   
        devs_sorted = sorted(devices, reverse = True, key=lambda d: d['step']) 
        for d in devs_sorted:
            if d['type'] == "PS":
                circuit.append(PS(np.radians(float(d['phi'])), d['modes'][0]['mode'], modes))
            if d['type'] == "BS":
                mode1 = -1
                mode2 = -1
                for m in d['modes']:
                    if m['my_port'] == "hybrid0":
                        mode1 = m['mode']
                    if m['my_port'] == "hybrid2":
                        mode2 = m['mode']
                # 26.07.2022 Sysoev, added random direction
                sign = 1
                if np.random.randint(low = 0, high = 2) % 2 == 0:
                    sign = -1
                theta = float(d['theta']) * (1.0 + sign*bs_error)
                circuit.append(BS(np.radians(theta), np.radians(float(d['phi'])), mode1, mode2, modes))
            if d['type'] == "User Project":
                circ = data.GetCircuit(d['project_key'])
                circ_proj = data.Project.get(d['project_key'])
                circ_devs, circ_modes, error = data.getDevsModes(circ_proj)
                circ_m, circ_inv, error = ConstructCircuitMatrixWithError(circ_devs, circ_modes, bs_error)
                circ_modes = [-1 for i in range(circ.modes)]
                for m in d['modes']:
                    index = int(m['my_port'][6:]) / 2
                    circ_modes[index] = m['mode']
                circuit.append(sub_circ(circ_m, modes, circ_modes))

        # matrix
        matrix = reduce(np.dot, circuit)
        inv = la.inv(matrix)
        return matrix, inv, ""        
    except Exception as ex:
        return None, None, "ConstructCircuitMatrixWithError: " + str(ex)        

def use_ancillas(input, ones, zeros):
    for i in ones:
        input = use_result(input, i, 1)
    for i in zeros:
        input = use_result(input, i, 0)
    return input

def check_circuit_modes_list(control_modes, dest_modes, ancilla_in_ones, ancilla_out_ones, ancilla_zeros, modes):
    if len(control_modes) != 2 or len(dest_modes) != 2:
        return False
    ancillas = len(ancilla_out_ones) + len(ancilla_zeros)
    if len(ancilla_in_ones) > ancillas:
        return False
    if ancillas + 4 != modes:
        return False
    return True

def use_input_ancillas(ancilla_in_ones):
    input = ""
    for i in ancilla_in_ones:
        input += "a" + str(i) + "*"
    if len(input) > 0:
        input = input[:-1]
    return input

def get_psi_0(input, control_modes, dest_modes):
    out = use_result(input, control_modes[1], 1)
    out = use_result(out, dest_modes[1], 1)     
    out = use_result(out, control_modes[0], 0)
    out = use_result(out, dest_modes[0], 0)     
    return complex(out)
def get_psi_1(input, control_modes, dest_modes):
    out = use_result(input, control_modes[1], 1)
    out = use_result(out, dest_modes[0], 1)     
    out = use_result(out, control_modes[0], 0)
    out = use_result(out, dest_modes[1], 0)     
    return complex(out)
def get_psi_2(input, control_modes, dest_modes):
    out = use_result(input, control_modes[0], 1)
    out = use_result(out, dest_modes[1], 1)     
    out = use_result(out, control_modes[1], 0)
    out = use_result(out, dest_modes[0], 0)     
    return complex(out)
def get_psi_3(input, control_modes, dest_modes):
    out = use_result(input, control_modes[0], 1)
    out = use_result(out, dest_modes[0], 1)     
    out = use_result(out, control_modes[1], 0)
    out = use_result(out, dest_modes[1], 0)     
    return complex(out)

def calc_psi_and_density(control_modes, dest_modes, ancilla_in_ones, ancilla_out_ones, ancilla_zeros, modes, matrix_inverse, state):
    if not check_circuit_modes_list(control_modes, dest_modes, ancilla_in_ones, ancilla_out_ones, ancilla_zeros, modes):
        return None, None, "Couldn't identify conditional gate"
    input = use_input_ancillas(ancilla_in_ones)

    # prepare state
    if len(input) > 0:
        input += "*"
    if state == "00":
        input = input + "a" + str(control_modes[1]) + "*a" + str(dest_modes[1])
    if state == "01":
        input = input + "a" + str(control_modes[1]) + "*a" + str(dest_modes[0])
    if state == "10":
        input = input + "a" + str(control_modes[0]) + "*a" + str(dest_modes[1])
    if state == "11":
        input = input + "a" + str(control_modes[0]) + "*a" + str(dest_modes[0])
    input = run_circuit(input, matrix_inverse, modes)
    input = use_ancillas(input, ancilla_out_ones, ancilla_zeros)

    # vector
    psi = np.zeros(4, dtype = 'complex_')
    psi[0] = get_psi_0(input, control_modes, dest_modes)
    psi[1] = get_psi_1(input, control_modes, dest_modes)
    psi[2] = get_psi_2(input, control_modes, dest_modes)
    psi[3] = get_psi_3(input, control_modes, dest_modes)

    result = np.identity(4, dtype = 'complex_')
    for i in range(4):
        for j in range(4):
            result[i][j] = psi[i] * np.conj(psi[j])
    return result, psi, ""

def calc_psi_and_density_XY(control_modes, dest_modes, ancilla_in_ones, ancilla_out_ones, ancilla_zeros, modes, matrix_inverse, state, basis, psi_00, psi_01, psi_10, psi_11):
    #temp, psi_00, error = calc_psi_and_density(control_modes, dest_modes, ancilla_in_ones, ancilla_out_ones, ancilla_zeros, modes, matrix_inverse, "00")
    #if error:
    #    return None, None, error
    #temp, psi_01, error = calc_psi_and_density(control_modes, dest_modes, ancilla_in_ones, ancilla_out_ones, ancilla_zeros, modes, matrix_inverse, "01")
    #temp, psi_10, error = calc_psi_and_density(control_modes, dest_modes, ancilla_in_ones, ancilla_out_ones, ancilla_zeros, modes, matrix_inverse, "10")
    #temp, psi_11, error = calc_psi_and_density(control_modes, dest_modes, ancilla_in_ones, ancilla_out_ones, ancilla_zeros, modes, matrix_inverse, "11")
    
    m1 = m2 = 1
    if state[0] == "-":
        m1 = -1
    if state[1] == "-":
        m2 = -1
    if basis == "X":
        psi = 0.5 * (psi_00 + m2*psi_01 + m1*psi_10 + m1*m2*psi_11)
    if basis == "Y":
        psi = 0.5 * (psi_00 + 1j*m2*psi_01 + 1j*m1*psi_10 - m1*m2*psi_11)

    result = np.identity(4, dtype = 'complex_')
    for i in range(4):
        for j in range(4):
            result[i][j] = psi[i] * np.conj(psi[j])
    return result, psi, ""        
    
def calc_density(control_modes, dest_modes, ancilla_in_ones, ancilla_out_ones, ancilla_zeros, modes, matrix_inverse, state, basis, psi_00, psi_01, psi_10, psi_11):
    if basis == "Z":
        res, psi, error = calc_psi_and_density(control_modes, dest_modes, ancilla_in_ones, ancilla_out_ones, ancilla_zeros, modes, matrix_inverse, state) 
    else:
        res, psi, error = calc_psi_and_density_XY(control_modes, dest_modes, ancilla_in_ones, ancilla_out_ones, ancilla_zeros, modes, matrix_inverse, state, basis, psi_00, psi_01, psi_10, psi_11) 
    return res, error

def calc_probability(control_modes, dest_modes, ancilla_in_ones, ancilla_out_ones, ancilla_zeros, modes, matrix_inverse):
    rho_00, error = calc_density(control_modes, dest_modes, ancilla_in_ones, ancilla_out_ones, ancilla_zeros, modes, matrix_inverse, "00")
    rho_01, error = calc_density(control_modes, dest_modes, ancilla_in_ones, ancilla_out_ones, ancilla_zeros, modes, matrix_inverse, "01")
    rho_10, error = calc_density(control_modes, dest_modes, ancilla_in_ones, ancilla_out_ones, ancilla_zeros, modes, matrix_inverse, "10")
    rho_11, error = calc_density(control_modes, dest_modes, ancilla_in_ones, ancilla_out_ones, ancilla_zeros, modes, matrix_inverse, "11")
    if error:
        return None, None, None, None, None, error
    p0 = abs(np.trace(rho_00))
    p1 = abs(np.trace(rho_01))
    p2 = abs(np.trace(rho_10))
    p3 = abs(np.trace(rho_11))
    min_prob = min([p0, p1, p2, p3])
    return [min_prob, p0, p1, p2, p3], ""

# can't use scipy in appengine  
# thanks to Tristan Nemoz for this answer:
# https://stackoverflow.com/questions/61262772/is-there-any-way-to-get-a-sqrt-of-a-matrix-in-numpy-not-element-wise-but-as-a  
def matrix_sqrt(a):
    # Computing diagonalization
    evalues, evectors = np.linalg.eig(a)
    # Ensuring square root matrix exists
    sqrt_matrix = reduce(np.dot, [evectors, np.diag(np.sqrt(evalues)), np.linalg.inv(evectors)])
    return sqrt_matrix
def calc_fidelity(rho_out, rho):
    tr_rho = np.trace(rho)
    tr_out = np.trace(rho_out)
    sqrt_rho = matrix_sqrt(rho)
    if tr_rho * tr_out == 0:
        return 0
    return abs(np.trace(matrix_sqrt(reduce(np.dot, [sqrt_rho, rho_out, sqrt_rho]))) ** 2 / (tr_rho * tr_out))

def calc_rho(gate, state):
    cgate = np.identity(4, dtype = 'complex_')
    if gate == "CZ":
        state[3] = -state[3]
    if gate == "CX":
        tmp = state[2]
        state[2] = state[3]
        state[3] = tmp
    if gate == "CY":
        tmp = 1j*state[2]
        state[2] = -1j*state[3]
        state[3] = tmp
    for i in range(4):
        for j in range(4):
            cgate[i][j] = state[i]*np.conj(state[j])
    return cgate
    
def calc_fidelity_values(rho, gate):
    result = np.zeros(13)

    #
    #   Z-base
    #
    for i in range(0, 4):
        v = np.zeros(4, dtype = "complex")
        v[i] = 1
        cz = calc_rho(gate, v)
        result[i+1] = min(1, calc_fidelity(rho[i], cz))
    #
    #   X-base
    #        
    for i in range(4, 8):
        v = np.ones(4, dtype = "complex")
        if i == 5:
            v[1] = -1
            v[3] = -1
        if i == 6:
            v[2] = -1
            v[3] = -1
        if i == 7:
            v[1] = -1
            v[2] = -1
        cz = calc_rho(gate, v)
        result[i+1] = min(1, calc_fidelity(rho[i], cz))
    #
    #   Y-base
    #        
    for i in range(8, 12):
        v = [1, 1j, 1j, -1]
        if i == 9:
            v[1] *= -1
            v[3] *= -1
        if i == 10:
            v[2] *= -1
            v[3] *= -1
        if i == 11:
            v[1] *= -1
            v[2] *= -1
        cz = calc_rho(gate, v)
        result[i+1] = min(1, calc_fidelity(rho[i], cz))

    result[0] = min(result[1:])
    return result



def get_fidelity(project_key):
    # check if we already did the calculation
    #circ = data.GetCircuit(project_key)
    #if circ:
    #    if circ.fidelities:
    #        return circ.fidelities

    fd, error = getCircuitFidelityData(project_key, 0.0)
    if error:
        return json.dumps({'error': True, 'data': error}, default=str)

    states = ["00", "01", "10", "11", "++", "+-", "-+", "--", "++", "+-", "-+", "--"]
    bases = ["Z", "Z", "Z", "Z", "X", "X", "X", "X", "Y", "Y", "Y", "Y"]

    Rho = [np.identity(4) for i in range(12)]
    P = np.zeros(12)

    temp_00, psi_00, error = calc_psi_and_density(fd['control_modes'], fd['dest_modes'], fd['ancilla_in_ones'], fd['ancilla_out_ones'], fd['ancilla_zeros'], fd['modes'], fd['matrix'], "00")
    if error:
        return json.dumps({'error': True, 'data': error}, default=str)
    temp_01, psi_01, error = calc_psi_and_density(fd['control_modes'], fd['dest_modes'], fd['ancilla_in_ones'], fd['ancilla_out_ones'], fd['ancilla_zeros'], fd['modes'], fd['matrix'], "01")
    temp_10, psi_10, error = calc_psi_and_density(fd['control_modes'], fd['dest_modes'], fd['ancilla_in_ones'], fd['ancilla_out_ones'], fd['ancilla_zeros'], fd['modes'], fd['matrix'], "10")
    temp_11, psi_11, error = calc_psi_and_density(fd['control_modes'], fd['dest_modes'], fd['ancilla_in_ones'], fd['ancilla_out_ones'], fd['ancilla_zeros'], fd['modes'], fd['matrix'], "11")

    Rho[0] = temp_00
    Rho[1] = temp_01
    Rho[2] = temp_10
    Rho[3] = temp_11
    for i in range(4):
        P[i] = min(1, abs(np.trace(Rho[i])))
        
    for i in range(4, 12):
        Rho[i], error = calc_density(fd['control_modes'], fd['dest_modes'], fd['ancilla_in_ones'], fd['ancilla_out_ones'], fd['ancilla_zeros'], fd['modes'], fd['matrix'], states[i], bases[i], psi_00, psi_01, psi_10, psi_11)
        P[i] = min(1, abs(np.trace(Rho[i])))
    if error:
        return json.dumps({'error': True, 'data': error}, default=str)
    min_prob = min(P)

    gate = "CZ"
    vals = calc_fidelity_values(Rho, gate)
    vals_cy = calc_fidelity_values(Rho, "CY")
    if vals_cy[0] > vals[0]:
        vals = vals_cy
        gate = "CY"
    vals_cx = calc_fidelity_values(Rho, "CX")
    if vals_cx[0] > vals[0]:
        vals = vals_cx
        gate = "CX"

    # error 1%
    fd, error = getCircuitFidelityData(project_key, 0.01)
    #fd_, error = getCircuitFidelityData(project_key, -0.01)
    if error:
        return json.dumps({'error': True, 'data': error}, default=str)

    Rho_1 = [np.identity(4) for i in range(12)]
    #Rho_1_ = [np.identity(4) for i in range(12)]
    P_1 = np.zeros(12)
    temp_00, psi_00, error = calc_psi_and_density(fd['control_modes'], fd['dest_modes'], fd['ancilla_in_ones'], fd['ancilla_out_ones'], fd['ancilla_zeros'], fd['modes'], fd['matrix'], "00")
    temp_01, psi_01, error = calc_psi_and_density(fd['control_modes'], fd['dest_modes'], fd['ancilla_in_ones'], fd['ancilla_out_ones'], fd['ancilla_zeros'], fd['modes'], fd['matrix'], "01")
    temp_10, psi_10, error = calc_psi_and_density(fd['control_modes'], fd['dest_modes'], fd['ancilla_in_ones'], fd['ancilla_out_ones'], fd['ancilla_zeros'], fd['modes'], fd['matrix'], "10")
    temp_11, psi_11, error = calc_psi_and_density(fd['control_modes'], fd['dest_modes'], fd['ancilla_in_ones'], fd['ancilla_out_ones'], fd['ancilla_zeros'], fd['modes'], fd['matrix'], "11")

    Rho_1[0] = temp_00
    Rho_1[1] = temp_01
    Rho_1[2] = temp_10
    Rho_1[3] = temp_11
    for i in range(4):
        P_1[i] = min(1, abs(np.trace(Rho_1[i])))
        
    for i in range(4, 12):
        Rho_1[i], error = calc_density(fd['control_modes'], fd['dest_modes'], fd['ancilla_in_ones'], fd['ancilla_out_ones'], fd['ancilla_zeros'], fd['modes'], fd['matrix'], states[i], bases[i], psi_00, psi_01, psi_10, psi_11)
        #Rho_1_[i], error = calc_density(fd_['control_modes'], fd_['dest_modes'], fd_['ancilla_in_ones'], fd_['ancilla_out_ones'], fd_['ancilla_zeros'], fd_['modes'], fd_['matrix'], states[i], bases[i])
        #P_1[i] = min(abs(np.trace(Rho_1[i])), abs(np.trace(Rho_1_[i])))
        P_1[i] = min(abs(np.trace(Rho_1[i])), 1)
    if error:
        return json.dumps({'error': True, 'data': error}, default=str)
    min_prob_1 = min(P_1)

    vals_1 = calc_fidelity_values(Rho_1, gate)
    #vals_1_ = calc_fidelity_values(Rho_1_, gate)
    #if vals_1_[0] < vals_1[0]:
    #    vals_1 = vals_1_

    # error 5%
    fd, error = getCircuitFidelityData(project_key, 0.05)
    #fd_, error = getCircuitFidelityData(project_key, -0.05)
    if error:
        return json.dumps({'error': True, 'data': error}, default=str)

    Rho_5 = [np.identity(4) for i in range(12)]
    #Rho_5_ = [np.identity(4) for i in range(12)]
    P_5 = np.zeros(12)
    temp_00, psi_00, error = calc_psi_and_density(fd['control_modes'], fd['dest_modes'], fd['ancilla_in_ones'], fd['ancilla_out_ones'], fd['ancilla_zeros'], fd['modes'], fd['matrix'], "00")
    temp_01, psi_01, error = calc_psi_and_density(fd['control_modes'], fd['dest_modes'], fd['ancilla_in_ones'], fd['ancilla_out_ones'], fd['ancilla_zeros'], fd['modes'], fd['matrix'], "01")
    temp_10, psi_10, error = calc_psi_and_density(fd['control_modes'], fd['dest_modes'], fd['ancilla_in_ones'], fd['ancilla_out_ones'], fd['ancilla_zeros'], fd['modes'], fd['matrix'], "10")
    temp_11, psi_11, error = calc_psi_and_density(fd['control_modes'], fd['dest_modes'], fd['ancilla_in_ones'], fd['ancilla_out_ones'], fd['ancilla_zeros'], fd['modes'], fd['matrix'], "11")

    Rho_5[0] = temp_00
    Rho_5[1] = temp_01
    Rho_5[2] = temp_10
    Rho_5[3] = temp_11
    for i in range(4):
        P_5[i] = min(1, abs(np.trace(Rho_5[i])))
        
    for i in range(4, 12):
        Rho_5[i], error = calc_density(fd['control_modes'], fd['dest_modes'], fd['ancilla_in_ones'], fd['ancilla_out_ones'], fd['ancilla_zeros'], fd['modes'], fd['matrix'], states[i], bases[i], psi_00, psi_01, psi_10, psi_11)
        #Rho_5_[i], error = calc_density(fd_['control_modes'], fd_['dest_modes'], fd_['ancilla_in_ones'], fd_['ancilla_out_ones'], fd_['ancilla_zeros'], fd_['modes'], fd_['matrix'], states[i], bases[i])
        P_5[i] = min(abs(np.trace(Rho_5[i])), 1)
    if error:
        return json.dumps({'error': True, 'data': error}, default=str)
    min_prob_5 = min(P_5)

    vals_5 = calc_fidelity_values(Rho_5, gate)
    #vals_5_ = calc_fidelity_values(Rho_5_, gate)
    #if vals_5_[0] < vals_5[0]:
    #    vals_5 = vals_5_

    fidelities = json.dumps({'error': False, 'data': {'p_0': [min_prob] + P.tolist(),
                                                'p_1': [min_prob_1] + P_1.tolist(),
                                                'p_5': [min_prob_5] + P_5.tolist(),
                                                'gate': gate,
                                                'vals_0': vals.tolist(), 
                                                'vals_1': vals_1.tolist(),
                                                'vals_5': vals_5.tolist()}})
    #if circ:
    #    circ.fidelities = fidelities
    #    circ.put()
    return fidelities

def process_complex_number(phi):
    r = phi.real
    im = phi.imag
    if abs(r) < 1e-12:
        r = 0
    if abs(im) < 1e-12:
        im = 0
        return r
    return r + 1j*im

def format_complex_number(phi, first):
    res = str(phi)
    res = sub(r'e-(\d+)', r'\cdot 10^{-\1}', res)
    if abs(phi.real) > 0 and abs(phi.imag) > 0:
        res = "(" + res + ")"
    if not first:
        if res[0] != "-":
            res = "+" + res
    res = sub(r'\.(\d{6})(\d+)', r'.\1', res)
    return res

#
#  Run C-Gate
#    
def get_cgate_run(project_key, base):
    base = base.lower()
    circ = data.GetCircuit(project_key)
    if circ:
        if base == "x" and circ.cgate_run_x:
            return circ.cgate_run_x, None
        if base == "y" and circ.cgate_run_y:
            return circ.cgate_run_y, None
        if base == "z" and circ.cgate_run_z:
            return circ.cgate_run_z, None
    fd, error = getCircuitFidelityData(project_key, 0.0)
    if error:
        return None, error
    rho_00, psi_00, error = calc_psi_and_density(fd['control_modes'], fd['dest_modes'], fd['ancilla_in_ones'], fd['ancilla_out_ones'], fd['ancilla_zeros'], fd['modes'], fd['matrix'], "00")
    rho_01, psi_01, error = calc_psi_and_density(fd['control_modes'], fd['dest_modes'], fd['ancilla_in_ones'], fd['ancilla_out_ones'], fd['ancilla_zeros'], fd['modes'], fd['matrix'], "01")
    rho_10, psi_10, error = calc_psi_and_density(fd['control_modes'], fd['dest_modes'], fd['ancilla_in_ones'], fd['ancilla_out_ones'], fd['ancilla_zeros'], fd['modes'], fd['matrix'], "10")
    rho_11, psi_11, error = calc_psi_and_density(fd['control_modes'], fd['dest_modes'], fd['ancilla_in_ones'], fd['ancilla_out_ones'], fd['ancilla_zeros'], fd['modes'], fd['matrix'], "11")
    if error:
        return None, error

    if base == "x":
        psi_0 = (psi_00 + psi_01 + psi_10 + psi_11) / 2
        psi_1 = (psi_00 - psi_01 + psi_10 - psi_11) / 2
        psi_2 = (psi_00 + psi_01 - psi_10 - psi_11) / 2
        psi_3 = (psi_00 - psi_01 - psi_10 + psi_11) / 2
        vects = ["++", "+-", "-+", "--"]
        basis1 = np.array([0.5, 0.5, 0.5, 0.5], dtype = "complex")
        basis2 = np.array([0.5, -0.5, 0.5, -0.5], dtype = "complex")
        basis3 = np.array([0.5, 0.5, -0.5, -0.5], dtype = "complex")
        basis4 = np.array([0.5, -0.5, -0.5, 0.5], dtype = "complex")
    if base == "y":
        psi_0 = (psi_00 + 1j*psi_01 + 1j*psi_10 - psi_11) / 2
        psi_1 = (psi_00 - 1j*psi_01 + 1j*psi_10 + psi_11) / 2
        psi_2 = (psi_00 + 1j*psi_01 - 1j*psi_10 + psi_11) / 2
        psi_3 = (psi_00 - 1j*psi_01 - 1j*psi_10 - psi_11) / 2
        vects = ["y_1 y_1", "y_1 y_2", "y_2 y_1", "y_2 y_2"]
        basis1 = np.array([0.5, 1j*0.5, 1j*0.5, 0.5], dtype = "complex")
        basis2 = np.array([0.5, -1j*0.5, 1j*0.5, -0.5], dtype = "complex")
        basis3 = np.array([0.5, 1j*0.5, -1j*0.5, -0.5], dtype = "complex")
        basis4 = np.array([0.5, -1j*0.5, -1j*0.5, 0.5], dtype = "complex")
    if base == "z":
        psi_0 = psi_00
        psi_1 = psi_01
        psi_2 = psi_10
        psi_3 = psi_11
        vects = ["00", "01", "10", "11"]
        basis1 = np.array([1, 0, 0, 0], dtype = "complex")
        basis2 = np.array([0, 1, 0, 0], dtype = "complex")
        basis3 = np.array([0, 0, 1, 0], dtype = "complex")
        basis4 = np.array([0, 0, 0, 1], dtype = "complex")
    cgate_run = "" 
    Psi = [psi_0, psi_1, psi_2, psi_3]
    basis = [basis1, basis2, basis3, basis4]
    for i in range(4):
        cgate_run += "\\(|" + vects[i] + "\\rangle \\rightarrow " 
        first = True
        for j in range(4):
            a = process_complex_number(np.dot(Psi[i], basis[j]))
            if abs(a) > 0:
                cgate_run += format_complex_number(a, first) + " |" + vects[j] + "\\rangle "
                first = False
        cgate_run += " \\)  <br> "

    if circ:
        if base == "x":
            circ.cgate_run_x = cgate_run
            circ.put()
        if base == "y":
            circ.cgate_run_y = cgate_run
            circ.put()
        if base == "z":
            circ.cgate_run_z = cgate_run
            circ.put()
    return cgate_run, None