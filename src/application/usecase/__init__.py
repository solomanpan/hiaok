"""Use cases = curried functions (services first, request data last).

The presentation layer registers them through FastAPI ``Depends`` by partially applying services.
"""
