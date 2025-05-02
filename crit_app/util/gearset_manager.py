def set_is_selected_fields(gearset_list: dict, index_to_set_true: int) -> dict:
    n_gearset = len(gearset_list)

    if not isinstance(index_to_set_true, int):
        return gearset_list
    if index_to_set_true > n_gearset:
        return gearset_list

    for idx in range(n_gearset):
        if idx == index_to_set_true:
            gearset_list[idx]["is_selected"] = True
        else:
            gearset_list[idx]["is_selected"] = False
    return gearset_list


def get_current_selection_index(gearset_list: list[dict]):
    if not gearset_list:
        return -1

    is_selected = [idx for idx, s in enumerate(gearset_list) if s["is_selected"]]

    if not is_selected:
        return -1
    else:
        return is_selected[0]


def create_gearset_selector_options(saved_gearsets: list[dict]) -> list[dict]:
    """
    Create options list for the default gearset selector dropdown.

    Includes a 'No Default' option.

    Args:
        saved_gearsets (list[dict]): The list of saved gearsets.

    Returns:
        list[dict]: A list of dictionaries suitable for dcc.Dropdown options.
    """
    # Start with the 'No Default' option
    options = [{"label": "No Default", "value": "-1"}]

    if saved_gearsets:
        options.extend(
            [
                {
                    "label": f"{gearset.get('name', 'Unnamed')} ({gearset.get('role', 'Unknown')})",
                    "value": str(i),
                }
                for i, gearset in enumerate(saved_gearsets)
            ]
        )
    return options


def is_valid_gearset_index(index: int | None, gearsets: list[dict]) -> bool:
    """Checks if the index is valid for accessing/modifying the gearsets list."""
    return index is not None and 0 <= index < len(gearsets)
