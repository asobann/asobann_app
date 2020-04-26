def compo_pos(browser, component):
    '''
    return position of the component relative to table
    :param browser:
    :param component:
    :return: { "top": <Number>, "left": <Number> }
    '''
    table = browser.find_element_by_css_selector("div.table")
    table_loc = table.location
    comp_loc = component.location
    return { "left": comp_loc["x"] - table_loc["x"], "top": comp_loc["y"] - table_loc["y"]}
