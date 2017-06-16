from artifacts import definitions
from artifacts import errors
from artifacts import reader
from artifacts import registry
from artifacts import source_type

from gluon import http
from rekall_lib.types import artifacts

import re
import yaml




TYPE_INDICATOR_REKALL_EFILTER = "REKALL_EFILTER"


class RekallEfilter(source_type.SourceType):

    TYPE_INDICATOR = TYPE_INDICATOR_REKALL_EFILTER

    def __init__(self, query=None, type_name=None, fields=None):
        if not query:
            raise errors.FormatError(u'Missing query value.')

        super(RekallEfilter, self).__init__()
        self.type_name = type_name
        self.fields = fields or []

    def AsDict(self):
        source_type_attributes = dict(query=self.query)
        if self.type_name:
            source_type_attributes["type_name"] = self.type_name

        if self.fields:
            source_type_attributes["fields"] = self.fields

        return source_type_attributes


artifact_registry = registry.ArtifactDefinitionsRegistry()
artifact_registry.RegisterSourceType(RekallEfilter)


def is_definition_in_db(current, name):
    db = current.db
    return db(db.artifacts.name == name).select().first()


def add(current, artifact):
    """Adds a new artifact to the database."""
    db = current.db
    decoded_artifacts = []
    artifact_snippets = re.split("^---$", artifact, flags=re.M | re.S)
    for snippet in artifact_snippets:
        decoded_artifact = yaml.safe_load(snippet)
        if not decoded_artifact:
            continue

        decoded_artifact = artifacts.Artifact.from_primitive(decoded_artifact)
        decoded_artifacts.append((decoded_artifact, snippet))

    for decoded_artifact, artifact_text in decoded_artifacts:
        try:
            artifact_reader = reader.YamlArtifactsReader()
            definition = artifact_reader.ReadArtifactDefinitionValues(
                decoded_artifact.to_primitive(False))
            if is_definition_in_db(current, definition.name):
                raise TypeError("Artifact name %s already in database." %
                                definition.name)

            for source in definition.sources:
                if (source.type_indicator ==
                    definitions.TYPE_INDICATOR_ARTIFACT_GROUP):
                    if not is_definition_in_db(current, source):
                        raise TypeError(
                            "Artifact group references %s which "
                            "is not known yet." % source)

            db.artifacts.insert(
                name=decoded_artifact.name,
                artifact_text=artifact_text,
                artifact=decoded_artifact)

        except Exception as e:
            raise http.HTTP(400, "Error: %s" % e)

    return dict()

add.args = dict(
    artifact="The YAML encoded artifact to add to the database."
)


def list(current):
    """Return all the known artifacts."""
    db = current.db
    result = []
    for row in db(db.artifacts.id > 0).select():
        result.append(dict(name=row.artifact.name,
                           artifact=row.artifact.to_primitive()))

    return dict(data=result)
