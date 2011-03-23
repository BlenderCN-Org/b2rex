

import xml.etree.ElementTree as ET


def attr_name(name):
    return name.lower().replace(' ', '_')

class RexSceneExporter(object):
    def export(self, scene, filename):
        """
        Export the given scene into given filename.
        """
        root = ET.Element('scene')
        for idx, obj in enumerate(scene.objects):
            self.export_object(obj, root, idx)
        tree = ET.ElementTree(root)
        tree.write(filename)

    def test(self):
        """
        Export current scene to a test file
        """
        import bpy
        self.export(bpy.context.scene, "/tmp/test.xml")

    def export_object(self, obj, root, idx):
        """
        Export the given blender object into a rex element tree
        """
        entity = ET.SubElement(root, 'entity')
        entity.set('id', str(idx))
        self.export_components(obj, entity)

    def export_components(self, obj, entity):
        """
        Export all components from the given object into a
        rex entity element tree.
        """
        for comp in obj.opensim.components:
            component = ET.SubElement(entity, 'component')
            component.set('type', comp.type)
            component.set('sync', '1')
            for attr in comp.attribute_names:
                value = getattr(comp, attr_name(attr))
                attribute = ET.SubElement(component, 'attribute')
                attribute.set('name', attr)
                attribute.set('value', self.format_attribute(value))

    def format_attribute(self, value):
        """
        Format the given value for inclusion into rex xml.
        """
        return str(value)
