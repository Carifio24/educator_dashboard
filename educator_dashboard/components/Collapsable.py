import solara
from solara.alias import rv

@solara.component
def Collapsable(children = [], header = "Show Table"):
    with rv.ExpansionPanels():
        with rv.ExpansionPanel():
            with rv.ExpansionPanelHeader():
                solara.Markdown(header)
            rv.ExpansionPanelContent(children=children)
                
    