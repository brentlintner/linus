from pygments.style import Style
from pygments.token import (
    Comment,
    Error,
    Generic,
    Keyword,
    Name,
    Number,
    Operator,
    Punctuation,
    String,
    Text
)

class EverforestDarkStyle(Style):
    name = "everforest-dark"

    # Color Palette
    # background = 000100
    # foreground = dcdcdc
    # black = 4b565c
    # blue = 7fbbb3
    # cyan = 83c092
    # green = a7c080
    # magenta = d699b6
    # red = e67e80
    # white = d3c6aa
    # yellow = dbbc7f
    # orange = 83C092

    line_number_color = "#627e79"
    background_color = None

    styles = {
        Comment: "noitalic #859289",
        Comment.Preproc: "noitalic #7fbbb3",
        Comment.Special: "noitalic bg:#ffffff",
        Keyword: "nobold #e67e80",
        Keyword.Pseudo: "nobold #d699b6",
        Keyword.Type: "nobold #e67e80",
        Keyword.Constant: "nobold #d699b6",
        Operator: "#e69875",
        Operator.Word: "#83C092",
        Name: "#d3c6aa",
        Name.Builtin: "#a7c080",
        Name.Function: "#a7c080",
        Name.Class: "#e67e80",
        Name.Namespace: "#dbbc7f",
        Name.Exception: "#e67e80",
        Name.Variable: "#d699b6",
        Name.Constant: "#d699b6",
        Name.Label: "#d3c6aa",
        Name.Entity: "#e67e80",
        Name.Attribute: "#7fbbb3",
        Name.Tag: "#a7c080",
        Name.Decorator: "bold #e67e80",
        String: "#83C092",
        String.Doc: "noitalic",
        String.Interpol: "noitalic #d3c6aa",
        String.Escape: "#83C092",
        String.Regex: "#83C092",
        String.Symbol: "#d699b6",
        String.Other: "#e67e80",
        Number: "#d699b6",
        Punctuation: "#d3c6aa",
        Generic.Heading: "bold #d3c6aa",
        Generic.Subheading: "bold #d3c6aa",
        Generic.Deleted: "#e67e80",
        Generic.Inserted: "#a7c080",
        Generic.Error: "#e67e80",
        Generic.Emph: "noitalic #dcdcdc",
        Generic.Strong: "bold #dcdcdc",
        Generic.EmphStrong: "bold #dcdcdc",
        Generic.Prompt: "bold #e67e80",
        Generic.Output: "#d3c6aa",
        Generic.Traceback: "#e67e80",
        Error: "border:#e67e80",
        Text: "#dcdcdc",
    }
