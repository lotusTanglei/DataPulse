"""Portable Draft 7 schemas shared with the browser's CSP-safe interpreter."""

from jsonschema import Draft7Validator
from referencing import Registry
from referencing.exceptions import Unresolvable
from referencing.jsonschema import DRAFT7

KEYWORDS = frozenset(
    {
        "$id",
        "$schema",
        "$ref",
        "$comment",
        "title",
        "description",
        "default",
        "examples",
        "type",
        "enum",
        "const",
        "multipleOf",
        "maximum",
        "exclusiveMaximum",
        "minimum",
        "exclusiveMinimum",
        "maxLength",
        "minLength",
        "pattern",
        "format",
        "items",
        "additionalItems",
        "contains",
        "maxItems",
        "minItems",
        "uniqueItems",
        "maxProperties",
        "minProperties",
        "required",
        "properties",
        "patternProperties",
        "additionalProperties",
        "dependencies",
        "propertyNames",
        "definitions",
        "allOf",
        "anyOf",
        "oneOf",
        "not",
        "if",
        "then",
        "else",
        "readOnly",
        "writeOnly",
        "contentMediaType",
        "contentEncoding",
    }
)
SCHEMA_MAPS = {"properties", "patternProperties", "definitions", "dependencies"}
SCHEMA_CHILDREN = {
    "items",
    "additionalItems",
    "contains",
    "additionalProperties",
    "propertyNames",
    "not",
    "if",
    "then",
    "else",
    "allOf",
    "anyOf",
    "oneOf",
}


def check_plugin_schema(schema: dict) -> None:
    Draft7Validator.check_schema(schema)
    root_uri = "urn:datapulse:plugin-schema"
    registry = Registry().with_resource(root_uri, DRAFT7.create_resource(schema)).crawl()

    def walk(value, resolver):
        if isinstance(value, list):
            for child in value:
                walk(child, resolver)
        elif isinstance(value, dict):
            resolver = resolver.in_subresource(DRAFT7.create_resource(value))
            if set(value) - KEYWORDS:
                raise ValueError("Plugin schemas support only JSON Schema Draft 7 keywords.")
            dialect = value.get("$schema")
            if dialect is not None and dialect not in {
                "http://json-schema.org/draft-07/schema#",
                "https://json-schema.org/draft-07/schema#",
                "http://json-schema.org/draft-07/schema",
                "https://json-schema.org/draft-07/schema",
            }:
                raise ValueError("Plugin schemas must use JSON Schema Draft 7.")
            reference = value.get("$ref")
            if reference is not None and (
                not isinstance(reference, str) or not reference.startswith("#")
            ):
                raise ValueError("Plugin schemas cannot reference external resources.")
            if reference is not None:
                try:
                    resolver.lookup(reference)
                except Unresolvable as error:
                    raise ValueError("Plugin schema references must resolve locally.") from error
            for key in SCHEMA_MAPS & value.keys():
                for child in value[key].values():
                    walk(child, resolver)
            for key in SCHEMA_CHILDREN & value.keys():
                walk(value[key], resolver)

    walk(schema, registry.resolver(root_uri))
