I want you to refactor the Vector DB logic so that we can use `qduant`. See https://github.com/qdrant/qdrant.


## Constraints
- We should keep the `VectorStore` abstraction.
- `fetaures_pipeline.config` will control which Vector DB technology and embedding model we choose.
- Aim to keep the current embedding model for `qduant`. `bge-small-en-v1.5`. If not possible, find an equivalent.

## Validation
For initial validation, create comprehensive unit tests.
