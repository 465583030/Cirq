# Copyright 2018 The Cirq Developers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import random

import numpy as np
import pytest

import cirq

X = np.array([[0, 1], [1, 0]])
Y = np.array([[0, -1j], [1j, 0]])
Z = np.array([[1, 0], [0, -1]])
H = np.array([[1, 1], [1, -1]]) * np.sqrt(0.5)
SQRT_X = np.array([[1, 1j], [1j, 1]])
c = np.exp(1j * np.pi / 4)
SQRT_SQRT_X = np.array([[1 + c, 1 - c], [1 - c, 1 + c]]) / 2
SWAP = np.array([[1, 0, 0, 0],
               [0, 0, 1, 0],
               [0, 1, 0, 0],
               [0, 0, 0, 1]])
CNOT = np.array([[1, 0, 0, 0],
               [0, 1, 0, 0],
               [0, 0, 0, 1],
               [0, 0, 1, 0]])
CZ = np.diag([1, 1, 1, -1])


@pytest.mark.parametrize('matrix', [
    X,
    cirq.kron(X, X),
    cirq.kron(X, Y),
    cirq.kron(X, np.eye(2))
])
def test_map_eigenvalues_identity(matrix):
    identity_mapped = cirq.map_eigenvalues(matrix, lambda e: e)
    assert np.allclose(matrix, identity_mapped)


@pytest.mark.parametrize('matrix,exponent,desired', [
    [X, 2, np.eye(2)],
    [X, 3, X],
    [Z, 2, np.eye(2)],
    [H, 2, np.eye(2)],
    [Z, 0.5, np.diag([1, 1j])],
    [X, 0.5, np.array([[1j, 1], [1, 1j]]) * (1 - 1j) / 2],
])
def test_map_eigenvalues_raise(matrix, exponent, desired):
    exp_mapped = cirq.map_eigenvalues(matrix, lambda e: complex(e)**exponent)
    assert np.allclose(desired, exp_mapped)


@pytest.mark.parametrize('f1,f2', [
    (H, X),
    (H * 1j, X),
    (H, SQRT_X),
    (H, SQRT_SQRT_X),
    (H, H),
    (SQRT_SQRT_X, H),
    (X, np.eye(2)),
    (1j * X, np.eye(2)),
    (X, 1j * np.eye(2)),
    (-X, 1j * np.eye(2)),
    (X, X),
] + [
    (cirq.testing.random_unitary(2), cirq.testing.random_unitary(2))
    for _ in range(10)
])
def test_kron_factor(f1, f2):
    p = cirq.kron(f1, f2)
    g, g1, g2 = cirq.kron_factor_4x4_to_2x2s(p)
    assert abs(np.linalg.det(g1) - 1) < 0.00001
    assert abs(np.linalg.det(g2) - 1) < 0.00001
    assert np.allclose(g * cirq.kron(g1, g2), p)


@pytest.mark.parametrize('f1,f2', [
    (cirq.testing.random_special_unitary(2),
     cirq.testing.random_special_unitary(2))
    for _ in range(10)
])
def test_kron_factor_special_unitaries(f1, f2):
    p = cirq.kron(f1, f2)
    g, g1, g2 = cirq.kron_factor_4x4_to_2x2s(p)
    assert np.allclose(cirq.kron(g1, g2), p)
    assert abs(g - 1) < 0.000001
    assert cirq.is_special_unitary(g1)
    assert cirq.is_special_unitary(g2)


def test_kron_factor_fail():
    with pytest.raises(ValueError):
        _ = cirq.kron_factor_4x4_to_2x2s(
            cirq.kron_with_controls(cirq.CONTROL_TAG, X))

    with pytest.raises(ValueError):
        _ = cirq.kron_factor_4x4_to_2x2s(np.diag([1, 1, 1, 1j]))


def recompose_so4(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    assert a.shape == (2, 2)
    assert b.shape == (2, 2)
    assert cirq.is_special_unitary(a)
    assert cirq.is_special_unitary(b)

    magic = np.array([[1, 0, 0, 1j],
                    [0, 1j, 1, 0],
                    [0, 1j, -1, 0],
                    [1, 0, 0, -1j]]) * np.sqrt(0.5)
    result = np.real(cirq.dot(np.conj(magic.T),
                              cirq.kron(a, b),
                              magic))
    assert cirq.is_orthogonal(result)
    return result


@pytest.mark.parametrize('m', [
    cirq.testing.random_special_orthogonal(4)
    for _ in range(10)
])
def test_so4_to_magic_su2s(m):
    a, b = cirq.so4_to_magic_su2s(m)
    m2 = recompose_so4(a, b)
    assert np.allclose(m, m2)


@pytest.mark.parametrize('a,b', [
    (cirq.testing.random_special_unitary(2),
     cirq.testing.random_special_unitary(2))
    for _ in range(10)
])
def test_so4_to_magic_su2s_known_factors(a, b):
    m = recompose_so4(a, b)
    a2, b2 = cirq.so4_to_magic_su2s(m)
    m2 = recompose_so4(a2, b2)

    assert np.allclose(m2, m)

    # Account for kron(A, B) = kron(-A, -B).
    if np.linalg.norm(a + a2) > np.linalg.norm(a - a2):
        assert np.allclose(a2, a)
        assert np.allclose(b2, b)
    else:
        assert np.allclose(a2, -a)
        assert np.allclose(b2, -b)


@pytest.mark.parametrize('mat', [
    np.diag([0, 1, 1, 1]),
    np.diag([0.5, 2, 1, 1]),
    np.diag([1, 1j, 1, 1]),
    np.diag([1, 1, 1, -1]),
])
def test_so4_to_magic_su2s_fail(mat):
    with pytest.raises(ValueError):
        cirq.so4_to_magic_su2s(mat)


def recompose_kak(g, a, v, b) -> np.ndarray:
    a1, a0 = a
    x, y, z = v
    b1, b0 = b
    xx = cirq.kron(X, X)
    yy = cirq.kron(Y, Y)
    zz = cirq.kron(Z, Z)

    a = cirq.kron(a1, a0)
    m = cirq.map_eigenvalues(xx * x + yy * y + zz * z,
                               lambda e: np.exp(1j * e))
    b = cirq.kron(b1, b0)

    return cirq.dot(a, m, b) * g


@pytest.mark.parametrize('x,y,z', [
    [(random.random() * 2 - 1) * np.pi * 2 for _ in range(3)]
    for _ in range(10)
])
def test_kak_canonicalize_vector(x, y, z):
    i = np.eye(2)
    m = recompose_kak(1, (i, i), (x, y, z), (i, i))

    g, (a1, a0), (x2, y2, z2), (b1, b0) = cirq.kak_canonicalize_vector(
        x, y, z)
    m2 = recompose_kak(g, (a1, a0), (x2, y2, z2), (b1, b0))

    assert 0.0 <= x2 <= np.pi / 4
    assert 0.0 <= y2 <= np.pi / 4
    assert -np.pi / 4 <= z2 <= np.pi / 4
    assert abs(x2) >= abs(y2) >= abs(z2)
    assert cirq.is_special_unitary(a1)
    assert cirq.is_special_unitary(a0)
    assert cirq.is_special_unitary(b1)
    assert cirq.is_special_unitary(b0)
    assert np.allclose(m, m2)


@pytest.mark.parametrize('m', [
    np.eye(4),
    SWAP,
    SWAP * 1j,
    CZ,
    CNOT,
    SWAP.dot(CZ),
] + [
    cirq.testing.random_unitary(4)
    for _ in range(10)
])
def test_kak_decomposition(m):
    g, (a1, a0), (x, y, z), (b1, b0) = cirq.kak_decomposition(m)
    m2 = recompose_kak(g, (a1, a0), (x, y, z), (b1, b0))
    assert np.allclose(m, m2)
