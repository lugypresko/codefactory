import copy
import pytest

from pyiceberg.expressions import And, EqualTo, Not, Or


def test_and_expression_deepcopy_succeeds():
    original_expr = And(EqualTo("x", 1), EqualTo("y", 2))
    copied_expr = copy.deepcopy(original_expr)

    # Assert that the deepcopy was successful and didn't raise an error
    assert copied_expr is not original_expr
    assert copied_expr == original_expr
    assert copied_expr.left is not original_expr.left
    assert copied_expr.right is not original_expr.right
    assert copied_expr.left == original_expr.left
    assert copied_expr.right == original_expr.right


def test_or_expression_deepcopy_succeeds():
    original_expr = Or(EqualTo("a", 1), EqualTo("b", 2))
    copied_expr = copy.deepcopy(original_expr)

    # Assert that the deepcopy was successful and didn't raise an error
    assert copied_expr is not original_expr
    assert copied_expr == original_expr
    assert copied_expr.left is not original_expr.left
    assert copied_expr.right is not original_expr.right
    assert copied_expr.left == original_expr.left
    assert copied_expr.right == original_expr.right


def test_not_expression_deepcopy_succeeds():
    original_expr = Not(EqualTo("z", 10))
    copied_expr = copy.deepcopy(original_expr)

    # Assert that the deepcopy was successful and didn't raise an error
    assert copied_expr is not original_expr
    assert copied_expr == original_expr
    assert copied_expr.expression is not original_expr.expression
    assert copied_expr.expression == original_expr.expression

