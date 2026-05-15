import sympy as sp
from sympy import lambdify
from sympy.physics.quantum import TensorProduct
from math import sqrt, pi, log

#
# Definitions
#
zero = sp.Matrix([1,0])
one = sp.Matrix([0,1])
plus = 1/sp.sqrt(2)*(zero + one)
I = sp.eye(2)

#
# returns True if number_i == number_j == 1
# numbering goes from left to right!
#
def check_binary_positions(number, i, j, n):
    return (number >> (n - i)) & 1 == (number >> (n - j)) & 1 == 1

#
# i, j - vertices
# n - Graph size
#
def cPhase(i, j, n):
  cP = sp.eye(2**n)
  for k in range(2**n):
    if(check_binary_positions(k, i, j, n)):
      cP[k,k] = -1
  return cP

#
# Initial state
#
def state(n):
  return sp.Matrix([1 for i in range(2**n)]) / (2**(n / 2))

#
# Cluster state
#
def create_cluster(graph):
    if graph == [] :
        return plus
    else :
        n = max(num for pair in graph for num in pair)
        st = state(n)
        for i,j in graph :
            st = cPhase(i,j,n)*st
    return st

#
# Inputs
#
def entangle_inputs(cluster, W):
    N = len(W)
    M = int(log(len(cluster), 2)) + 1
    inputs = []
    a = sp.symbols(f'a:{N}')
    b = sp.symbols(f'b:{N}')
    for i in range(N):
        inputs.append(a[i]*zero+b[i]*one)
    for i,s in zip(W,inputs):
        cluster = cPhase(i, M, M) * TensorProduct(cluster, s)
        M += 1
    return cluster

#
# Transorms the state to the eigen-basis of the observables
# thetas - array of [node_number, theta]
# Observable A = Cos\theta X + Sin\theta Y
#
# S, invS - basis change matrices (diagonalizes A)
#
theta = sp.symbols('theta')
S = 1/sp.sqrt(2)*sp.Matrix([[1,1],[sp.exp(1j*theta),-sp.exp(1j*theta)]])
invS = 1/sp.sqrt(2)*sp.Matrix([[1,sp.exp(-1j*theta)],[1,-sp.exp(-1j*theta)]])

def measurement_basis(cluster, thetas):
    nums = [n[0] for n in thetas]
    angles = [a[1] for a in thetas]

    M = sp.log(len(cluster), 2)
    k = 0
    # the array of basis changes (for each node)
    ops = []
    for i in range(1, M + 1) :
        if i in nums:
            ops.append(invS.subs(theta, angles[k]))
            k += 1
        else :
            ops.append(I)
    return TensorProduct(*ops)*cluster

#
# returns the array of indexes which survive the specified measurement result
#
# q - the node number
# s - the result (0 for |0>, 1 for |1>)
#
def result(q, s, state) :
  m = state.rows
  bits = int(log(m, 2))
  res = set()
  for i in range(m) :
    if (i >> (bits - q)) & 1 == s:
      res.add(i)
  return res

#
# finally applies the measurement
# TODO: normalization
#
def reduce(cluster, results) :
    M = len(cluster)
    R = set(range(M))
    for q,s in results :
        R &= result(q,s,cluster)
    filtered_rows = [cluster[i, 0] for i in range(cluster.rows) if i in R]
    return sp.Matrix(filtered_rows)

#
#
# Arbitrary ONE-WAY computation
#
# graph - array of node pairs
# ins - array of node numbers to entangle inputs to
# observables - array of [n, theta], n - the node, theta - the angle
# results - array of [n, res], n - the node, res in {0, 1} - the measurement result
#
#
# Example:
# graph = [[1, 2], [2, 3], [3, 4]]
# ins = [1, 2, 3]
# observables = [[1, 0.5], [2, 0.5], [3, 0.5]]
# results = [[1, 0], [2, 0], [3, 0]]
# 
#
def universal_transformation(graph, ins, observables, results) :
    cluster = create_cluster(graph)
    cluster = entangle_inputs(cluster, ins)
    cluster = measurement_basis(cluster, observables)
    return reduce(cluster, results)