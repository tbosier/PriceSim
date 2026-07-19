"""FastAPI backend for the foundry pricing simulator.

This package is a thin serialization layer over the core engine. It imports the
simulation, scheduling, and config functions and exposes them over HTTP; it does
not reimplement any pricing or scheduling logic.
"""
