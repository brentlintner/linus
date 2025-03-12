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

    background_color = None # OR: #0f0f0f
    line_number_color = "#627e79"

    styles = {
        Comment: "noitalic #859289",
        Comment.Preproc: "noitalic #7fbbb3",
        Comment.Special: "noitalic bg:#ffffff",
        Keyword: "bold #e67e80",
        Keyword.Pseudo: "nobold #dcdcdc",
        Keyword.Type: "nobold #e67e80",
        Operator: "#e69875",
        Operator.Word: "bold #e67e80",
        Name: "#d3c6aa",
        Name.Builtin: "#d699b6",
        Name.Function: "#a7c080",
        Name.Class: "#e67e80",
        Name.Namespace: "#e67e80",
        Name.Exception: "#e67e80",
        Name.Variable: "#d699b6",
        Name.Constant: "#d699b6",
        Name.Label: "bold #d3c6aa",
        Name.Entity: "bold #e67e80",
        Name.Attribute: "#7fbbb3",
        Name.Tag: "bold #a7c080",
        Name.Decorator: "bold #e69875",
        String: "#83C092",
        String.Doc: "noitalic",
        String.Interpol: "noitalic #d3c6aa",
        String.Escape: "bold #83C092",
        String.Regex: "#83C092",
        String.Symbol: "#d699b6",
        String.Other: "#e69875",
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
        Generic.Prompt: "bold #e69875",
        Generic.Output: "#d3c6aa",
        Generic.Traceback: "#e67e80",
        Error: "border:#e67e80",
        Text: "#dcdcdc",
    }
