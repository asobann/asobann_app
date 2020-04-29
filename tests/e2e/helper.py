class Rect:
    top: float
    left: float
    bottom: float
    right: float
    height: float
    width: float

    def __init__(self, top=None, left=None, bottom=None, right=None, height=None, width=None):
        self.top = top
        self.left = left
        self.bottom = bottom
        self.right = right
        self.height = height
        self.width = width

    def __str__(self):
        return f"Rect(top={self.top}, left={self.left}, bottom={self.bottom}, right={self.right}, height={self.height}, width={self.width})"

    def __eq__(self, other):
        if type(other) != Rect:
            return False
        return (self.top == other.top and self.left == other.left
                and self.bottom == other.bottom and self.right == other.right
                and self.height == other.height and self.width == other.width)


def compo_pos(browser, component) -> Rect:
    """
    return position of the component relative to table
    :param browser: WebDriver
    :param component: component to get position
    :return: { "top": Number, "left": Number }
    """
    table = browser.find_element_by_css_selector("div.table")
    table_loc = table.location
    comp_loc = component.location
    return Rect(left=comp_loc["x"] - table_loc["x"], top=comp_loc["y"] - table_loc["y"])


