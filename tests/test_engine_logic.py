from unittest.mock import patch, MagicMock

import pytest

from business_rules import engine
from business_rules.variables import BaseVariables
from business_rules.operators import BaseType, StringType
from business_rules.actions import BaseActions


@patch.object(engine, "run")
def test_run_all_some_rule_triggered(_mock_engine_run: MagicMock) -> None:
    """By default, does not stop on first triggered rule. Returns True if
    any rule was triggered, otherwise False
    """
    rule1 = {"conditions": "condition1", "actions": "action name 1"}
    rule2 = {"conditions": "condition2", "actions": "action name 2"}
    variables = BaseVariables()
    actions = BaseActions()

    def return_action1(rule, *args, **kwargs):
        return rule["actions"] == "action name 1"

    engine.run.side_effect = return_action1

    result = engine.run_all([rule1, rule2], variables, actions)
    assert result is True
    assert engine.run.call_count == 2

    # switch order and try again
    engine.run.reset_mock()

    result = engine.run_all([rule2, rule1], variables, actions)
    assert result is True
    assert engine.run.call_count == 2


@patch.object(engine, "run", return_value=True)
def test_run_all_stop_on_first(_mock_engine_run: MagicMock) -> None:
    rule1 = {"conditions": "condition1", "actions": "action name 1"}
    rule2 = {"conditions": "condition2", "actions": "action name 2"}
    variables = BaseVariables()
    actions = BaseActions()

    result = engine.run_all(
        [rule1, rule2], variables, actions, stop_on_first_trigger=True
    )
    assert result is True
    assert engine.run.call_count == 1
    engine.run.assert_called_once_with(rule1, variables, actions)


@patch.object(engine, "check_conditions_recursively", return_value=True)
@patch.object(engine, "do_actions")
def test_run_that_triggers_rule(
    _mock_do_actions: MagicMock, _mock_check_conditions_recursively: MagicMock
) -> None:
    rule = {"conditions": "blah", "actions": "blah2"}
    variables = BaseVariables()
    actions = BaseActions()

    result = engine.run(rule, variables, actions)
    assert result is True
    engine.check_conditions_recursively.assert_called_once_with(
        rule["conditions"], variables
    )
    engine.do_actions.assert_called_once_with(rule["actions"], actions)


@patch.object(engine, "check_conditions_recursively", return_value=False)
@patch.object(engine, "do_actions")
def test_run_that_doesnt_trigger_rule(
    _mock_do_actions: MagicMock, _mock_check_conditions_recursively: MagicMock
) -> None:
    """
    DOCUMENT ME.
    """
    rule = {"conditions": "blah", "actions": "blah2"}
    variables = BaseVariables()
    actions = BaseActions()
    # set up
    result = engine.run(rule, variables, actions)
    assert result is False
    engine.check_conditions_recursively.assert_called_once_with(
        rule["conditions"], variables
    )
    assert engine.do_actions.call_count == 0


def test_do_actions() -> None:
    actions = [
        {"name": "action1"},
        {"name": "action2", "params": {"param1": "foo", "param2": 10}},
    ]
    defined_actions = BaseActions()
    defined_actions.action1 = MagicMock()
    defined_actions.action2 = MagicMock()

    engine.do_actions(actions, defined_actions)

    defined_actions.action1.assert_called_once_with()
    defined_actions.action2.assert_called_once_with(param1="foo", param2=10)


def test_check_operator_comparison() -> None:
    string_type = StringType("yo yo")
    with patch.object(string_type, "contains", return_value=True):
        result = engine._do_operator_comparison(string_type, "contains", "its mocked")
        assert result is True
        string_type.contains.assert_called_once_with("its mocked")


@patch.object(engine, "check_condition", return_value=True)
def test_check_all_conditions_with_all_true(_mock_check_condition: MagicMock) -> None:
    # set up
    conditions = {"all": [{"thing1": ""}, {"thing2": ""}]}
    variables = BaseVariables()
    # test
    result = engine.check_conditions_recursively(conditions, variables)
    assert result is True
    # assert call count and most recent call are as expected
    assert engine.check_condition.call_count == 2
    engine.check_condition.assert_called_with({"thing2": ""}, variables)


@patch.object(engine, "check_condition", return_value=False)
def test_check_all_conditions_with_all_false(_mock_check_condition: MagicMock) -> None:
    # set up
    conditions = {"all": [{"thing1": ""}, {"thing2": ""}]}
    variables = BaseVariables()
    # test
    result = engine.check_conditions_recursively(conditions, variables)
    assert result is False
    engine.check_condition.assert_called_once_with({"thing1": ""}, variables)


def test_check_all_and_any_together() -> None:
    conditions = {"any": [], "all": []}
    variables = BaseVariables()
    with pytest.raises(
        ValueError,
        match="Only one of 'not', 'any', or 'all' can be at the same level in the conditions dict",
    ):
        engine.check_conditions_recursively(conditions, variables)


def test_check_all_conditions_with_no_items_fails() -> None:
    with pytest.raises(
        ValueError, match="'all' conditions must have at least one child condition"
    ):
        engine.check_conditions_recursively({"all": []}, BaseVariables())


@patch.object(engine, "check_condition", return_value=True)
def test_check_any_conditions_with_all_true(_mock_check_condition: MagicMock) -> None:
    conditions = {"any": [{"thing1": ""}, {"thing2": ""}]}
    variables = BaseVariables()

    result = engine.check_conditions_recursively(conditions, variables)
    assert result is True
    engine.check_condition.assert_called_once_with({"thing1": ""}, variables)


@patch.object(engine, "check_condition", return_value=False)
def test_check_any_conditions_with_all_false(_mock_check_condition: MagicMock) -> None:
    conditions = {"any": [{"thing1": ""}, {"thing2": ""}]}
    variables = BaseVariables()

    result = engine.check_conditions_recursively(conditions, variables)
    assert result is False
    # assert call count and most recent call are as expected
    assert engine.check_condition.call_count == 2
    engine.check_condition.assert_called_with({"thing2": ""}, variables)


def test_check_any_condition_with_no_items_fails() -> None:
    with pytest.raises(
        ValueError, match="'any' conditions must have at least one child condition"
    ):
        engine.check_conditions_recursively({"any": []}, BaseVariables())


@patch.object(engine, "check_condition")
def test_nested_all_and_any(_mock_check_condition: MagicMock) -> None:
    # test
    conditions = {"all": [{"any": [{"name": 1}, {"name": 2}]}, {"name": 3}]}
    bv = BaseVariables()

    def side_effect(condition, _):
        return condition["name"] in [2, 3]

    engine.check_condition.side_effect = side_effect
    # test
    engine.check_conditions_recursively(conditions, bv)
    assert engine.check_condition.call_count == 3
    engine.check_condition.assert_any_call({"name": 1}, bv)
    engine.check_condition.assert_any_call({"name": 2}, bv)
    engine.check_condition.assert_any_call({"name": 3}, bv)


@pytest.mark.parametrize("other_key", ["all", "any"])
def test_check_not_with_all_any(other_key: str) -> None:
    """
    DOCUMENT ME.
    """
    conditions = {"not": [], other_key: []}
    variables = BaseVariables()
    with pytest.raises(
        ValueError,
        match="Only one of 'not', 'any', or 'all' can be at the same level in the conditions dict",
    ):
        engine.check_conditions_recursively(conditions, variables)


@pytest.mark.parametrize(
    "check_condition_result, expected_result", [(True, False), (False, True)]
)
def test_check_not_negates_result(
    check_condition_result: bool, expected_result: bool
) -> None:
    """
    DOCUMENT ME.
    """
    conditions = {"not": {"thing1": ""}}
    variables = BaseVariables()

    with patch.object(
        engine, "check_condition", return_value=check_condition_result
    ) as mock_check_condition:
        result = engine.check_conditions_recursively(conditions, variables)
    assert result is expected_result
    mock_check_condition.assert_called_once_with({"thing1": ""}, variables)


def test_do_with_invalid_action() -> None:
    actions = [{"name": "fakeone"}]
    err_string = "Action fakeone is not defined in class BaseActions"
    with pytest.raises(AssertionError, match=err_string):
        engine.do_actions(actions, BaseActions())


@pytest.mark.parametrize(
    ("str_variable_value", "expected"),
    [
        ("test_value", True),
        ("unmatched_test_value", False),
    ],
)
def test_check_condition_with_value(str_variable_value: str, expected: str) -> None:
    """
    DOCUMENT ME.
    """
    condition = {"name": "name", "operator": "equal_to", "value": "test_value"}
    with patch.object(
        engine, "_get_variable_value", return_value=StringType(str_variable_value)
    ):
        assert engine.check_condition(condition, BaseVariables()) is expected


@pytest.mark.parametrize(
    ("var1_value", "var2_value", "expected"),
    [("test_value", "test_value", True), ("test_value", "test_value_2", False)],
)
def test_check_condition_with_other_variable_name(
    var1_value: str, var2_value: str, expected: bool
) -> None:
    """
    DOCUMENT ME.
    """
    condition = {"name": "var1", "operator": "equal_to", "other_variable_name": "var2"}

    def get_variable_value_side_effect(_, name: str) -> BaseType:
        return {"var1": StringType(var1_value), "var2": StringType(var2_value)}[name]

    with patch.object(
        engine, "_get_variable_value", new=get_variable_value_side_effect
    ):
        assert engine.check_condition(condition, BaseVariables()) is expected


def test_check_condition_raises_if_both_value_and_other_name_missing() -> None:
    """
    DOCUMENT ME.
    """
    condition = {
        "name": "name",
        "operator": "operator",
    }
    with (
        patch.object(
            engine, "_get_variable_value", return_value=StringType("test_value")
        ),
        pytest.raises(
            ValueError,
            match="Condition must have a 'value' or 'other_variable_name' key",
        ),
    ):
        engine.check_condition(condition, BaseVariables())
