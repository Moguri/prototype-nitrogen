import panda3d.core as p3d


def _make_sdf_circle():
    return p3d.Texture()


_SDF_CIRCLE = _make_sdf_circle()


_RI_VERT = """
#version 130
uniform mat4 p3d_ModelViewProjectionMatrix;

in vec4 p3d_Vertex;
in vec2 p3d_MultiTexCoord0;

out vec2 texcoord;

void main() {
    texcoord = p3d_MultiTexCoord0;
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
}
"""


_RI_FRAG = """
#version 130
uniform sampler2D sdftex;

in vec2 texcoord;

out vec4 o_color;

void main() {
    o_color = vec4(1.0, 0.0, 0.0, 8.0);
}
"""


_SHADER = p3d.Shader.make(p3d.Shader.SL_GLSL, _RI_VERT, _RI_FRAG)


class RangeIndicator:
    def __init__(self, shape, **kwargs):
        cardmaker = p3d.CardMaker('RI_' + shape)
        cardmaker.set_frame(-1, 1, -1, 1)
        card = p3d.NodePath(cardmaker.generate())
        sdftex = None
        scale = p3d.LVector3(1.0, 1.0, 1.0)

        if shape == 'circle':
            sdftex = _SDF_CIRCLE
            scale *= kwargs['radius']
        else:
            raise ValueError("Unknown shape for RangeIndicator: {}".format(shape))

        card.set_scale(scale)
        card.set_p(-90)

        card.set_shader(_SHADER)
        #card.set_shader_input('sdftex', sdftex)

        self.graphics = card

    @property
    def visible(self):
        return not self.graphics.is_hidden()

    @visible.setter
    def visible(self, value):
        if value:
            self.graphics.show()
        else:
            self.graphics.hide()
