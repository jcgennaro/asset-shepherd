# Controlled mutations

Mutation code and manifests live here. Scripts must operate on copies, hash the source before and
after, emit a typed manifest, reload the variant independently, and preserve geometry/material/
texture content except where the manifest explicitly defines the stress case.
