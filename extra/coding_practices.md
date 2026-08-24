# Coding Practices Across the DeepMind Research Projects

## Purpose and How to Read This Guide

This document describes coding practices and implementation patterns observed
across this repository. It is an evidence-based guide to the code as released,
not a generic Python or machine-learning style guide.

The repository contains publication-scoped research releases rather than one
application with one architecture. A practice is called "common" when it
appears independently in multiple applicable projects. Framework-specific and
language-specific practices are identified separately.

The guide is organized from general to specialized:

1. Repository and module organization.
2. Core Python constructs, including their normal scope and implementation.
3. APIs, numerical code, data, training, and reproducibility.
4. Testing, executable workflows, frameworks, and other languages.

Historical compatibility code is evidence about the release that contains it,
not necessarily a recommendation for new work. TensorFlow 1, Sonnet 1, old
dependency pins, and Python 2 compatibility imports should not be copied into a
new project without a compatibility requirement.

## Audit Scope and Prevalence

The audit covered all 65 top-level project directories and all code-bearing
artifacts in the repository:

- 440 Python files, all of which parse successfully.
- 37 Jupyter notebooks, including every code cell.
- 44 shell scripts.
- 24 Racket modules and one Scribble document in `satore`.
- 12 Lua modules in `tvt/dmlab`.
- Four protobuf schemas in `cadl`.
- Three C/C++ source or header files and two Bazel files in
  `density_functional_approximation_dm21`.

Repository-level observations are:

| Observation | Evidence |
| --- | ---: |
| Project directories with a README | 65 of 65 |
| Python files with a copyright header | 440 of 440 |
| Python files with a module docstring | 423 of 440 |
| Python functions using snake_case | 3,888 of 3,919 |
| Python classes using CamelCase | 647 of 652 |
| Python lines no longer than 80 characters | 99.8% |
| Projects using Abseil application entry points | 34 |
| Projects with explicit invalid-value handling | 34 |
| Projects with explicit tensor or array shape checks | 30 |
| Projects containing automated tests | 25 |
| Projects containing notebooks | 26 |
| Projects with their own `requirements.txt` | 40 |

The core Python constructs have the following prevalence. "Projects" counts
top-level projects containing the construct in a `.py` file.

| Construct | Occurrences | Files | Projects |
| --- | ---: | ---: | ---: |
| Functions and methods | 3,919 | 407 | 43 |
| Classes | 652 | 249 | 41 |
| `if` statements | 3,216 | 353 | 43 |
| `for` loops | 966 | 263 | 41 |
| `while` loops | 56 | 39 | 20 |
| List comprehensions | 389 | 130 | 36 |
| Dictionary comprehensions | 93 | 51 | 25 |
| Generator expressions | 115 | 44 | 18 |
| `with` statements | 270 | 120 | 35 |
| `try` statements | 37 | 30 | 17 |
| Explicit `raise` statements | 472 | 163 | 37 |
| `assert` statements | 314 | 115 | 33 |
| `yield` or `yield from` | 54 | 25 | 12 |

These labels are used throughout:

- **Near-universal:** present in almost every applicable project.
- **Widespread:** present across many independent projects.
- **Recurring:** repeated, but not a repository-wide requirement.
- **Specialized:** used at a narrow technical boundary.
- **Framework-specific:** common only within a technology family.

Counts describe prevalence, not quality. A construct can be rare because the
need is rare; `try` is a good example. The code generally raises errors directly
and catches them only where recovery is possible.

## Part I: Repository and Source Organization

### Keep each project publication-scoped and self-contained

**Near-universal.** Each top-level directory owns the implementation, data
instructions, dependencies, examples, and citation information for one paper or
research artifact. Cross-project shared infrastructure is deliberately limited.

- Put project documentation in the project's `README.md`.
- Keep imports under the owning package, such as `from wikigraphs import utils`.
- Put dependency constraints beside the project.
- Avoid dependencies between unrelated publication directories.

Representative examples include [BYOL](byol/README.md),
[MeshGraphNets](meshgraphnets/README.md), and
[WikiGraphs](wikigraphs/README.md).

### Separate modules by scientific responsibility

**Widespread.** Larger releases divide code by behavior:

- Model definitions live in `model.py`, `networks.py`, or a `models/` package.
- Dataset parsing and preprocessing live in `dataset.py`, `reader.py`, or data
  utility modules.
- Training modules own update and orchestration logic.
- Evaluation and plotting live outside the model definition.
- Configuration lives in a config module, `configs/`, or `get_config()`.
- Checkpointing, normalization, schedules, and tokenization have narrow helpers.

This is more than file naming. Model modules generally do not parse flags,
dataset modules generally do not run training loops, and executable modules
assemble rather than implement the scientific components. See
[learning_to_simulate](learning_to_simulate), [ogb_lsc](ogb_lsc), and
[physics_inspired_models](physics_inspired_models).

### Keep entry points thin

**Widespread.** An executable module normally defines flags, validates the
invocation, constructs dependencies, and calls reusable library functions.
Mathematics and data processing remain importable without executing the
program. Examples include [wikigraphs/main.py](wikigraphs/main.py),
[learning_to_simulate/train.py](learning_to_simulate/train.py), and
[geomancer/train.py](geomancer/train.py).

### Prefer domain-specific helpers over miscellaneous utilities

**Recurring.** A helper belongs near the subsystem whose invariant it protects.
Use a general `utils.py` only for genuinely cross-cutting behavior. Examples of
focused helper modules include [byol/utils](byol/utils),
[learning_to_simulate/connectivity_utils.py](learning_to_simulate/connectivity_utils.py),
and [wikigraphs/wikigraphs/data/tokenizers.py](wikigraphs/wikigraphs/data/tokenizers.py).

### Preserve project-local dependency cohorts

**Widespread.** Forty projects provide their own `requirements.txt`. This is
important for JAX/JAXlib, TensorFlow, Sonnet, CUDA-sensitive dependencies, and
experimental libraries whose APIs changed rapidly.

When maintaining a release, preserve its compatible dependency cohort. For new
work, select current compatible versions together; do not copy old pins merely
because they exist here. Only add packaging metadata when external installation
is supported. Ten projects provide `setup.py`, including
[byol/setup.py](byol/setup.py) and [wikigraphs/setup.py](wikigraphs/setup.py).

### Match the established source style

**Near-universal for Python.** The observed Python style uses two-space block
indentation, an approximately 80-character line limit, `snake_case` functions
and variables, `CamelCase` classes, and `UPPER_CASE` constants. Multiline calls
use parentheses, trailing commas, and indentation that keeps argument structure
visible. Test methods occasionally retain old `unittest` camelCase names; that
is a compatibility exception rather than the dominant convention.

Comments explain intent, invariants, tensor shapes, units, or fidelity to a
paper. They do not merely restate an expression. TODOs are specific and follow
the surrounding project's ownership or issue-reference convention.

Lint and type-checker suppressions are local: `pylint` directives occur in 27
projects and `pytype` directives in 16. They cover framework-generated members,
intentional signature differences, notebook exports, or mathematical notation
that a tool cannot infer. Prefer the narrowest disable and re-enable it after
the exceptional region.

## Part II: Core Python Constructs and Scope

### Modules define ownership and visibility

**Near-universal.** Modules begin with a license header and usually a concise
module docstring. Imports are grouped into standard-library, third-party, and
local sections. Internal imports normally use an absolute project path so that
`python -m package.module` and test imports behave consistently.

Established aliases include `numpy as np`, `jax.numpy as jnp`, `haiku as hk`,
`sonnet as snt`, and `tensorflow.compat.v1 as tf` in TensorFlow 1 code. A
leading underscore marks implementation-private module names, functions, and
state. Upper-case names hold constants or flag-independent fixed values.

Module scope is mainly used for definitions: imports, constants, flags,
configuration tables, functions, and classes. Expensive work and data loading
normally occur in functions or guarded entry points, not during import.

### Functions are the default unit of computation

The 3,919 Python functions divide by lexical scope as follows:

| Function scope | Count | Normal role |
| --- | ---: | --- |
| Class method body | 2,244 | Behavior that owns or uses object state |
| Module level | 1,348 | Reusable transformations, builders, losses, and helpers |
| Nested in another function | 327 | Local callbacks, closures, wrappers, or transformed functions |

**Module functions** hold stateless or explicitly state-passing computation.
Numerical helpers, schedules, parsers, loss functions, and factories commonly
use this scope because they can be imported and tested independently.

**Methods** are used when behavior belongs to a model, environment, iterator,
checkpoint manager, or experiment lifecycle. Mutable fields are normally
private instance attributes such as `self._params` or `self._iterator`.

**Nested functions** keep a callback close to its one caller or capture factory
configuration. For example, [wikigraphs/utils.py](wikigraphs/utils.py) selects
and returns a model-specific loss function, while
[kfac_ferminet_alpha/utils.py](kfac_ferminet_alpha/utils.py) returns a wrapper
that conditionally applies a collective operation.

Nested functions usually capture values without rebinding them: there are no
`nonlocal` statements in the Python source. Explicit module-global mutation
occurs only once, for the lazy `_ALL_CLIPS` cache in
[catch_carry/mocap_data.py](catch_carry/mocap_data.py). Prefer arguments,
returns, object fields, or an explicit cache over new mutable globals.

Function signatures use defaults where a behavior has a clear standard mode;
keyword-only arguments appear where positional calls would be ambiguous.
`*args` and `**kwargs` mainly occur at framework extension points, decorators,
and factory forwarding boundaries. They should not hide an otherwise stable
public contract.

### Use conditionals to expose decisions and exit early

**Near-universal.** All Python-bearing projects use `if`. Common scopes are:

- At a public boundary, validate an input and raise immediately.
- At the top of a function, return early when no work is required.
- In factories, select one implementation and reject unknown choices.
- In training or evaluation, separate mode-dependent behavior explicitly.
- In loops, skip invalid or padded elements with `continue`, or stop with
  `break` when a terminal condition is reached.

Guard or control-exit branches occur extensively: 847 `if` bodies contain a
direct `return`, `raise`, `break`, or `continue`. This keeps the main path less
nested. An example is the model-type selection in
[wikigraphs/utils.py](wikigraphs/utils.py), which constructs one callable or
raises `ValueError` for an unknown type.

Use `elif` when alternatives are mutually exclusive. Conditional expressions
are common for short value selection, but multi-step work remains in normal
branches. `isinstance` checks are used at dynamic API boundaries; they should
not replace a stable polymorphic interface when classes already share one.

### Choose iteration according to the data flow

**Widespread.** The repository strongly favors `for` over `while`:

- `for item in collection` traverses datasets, parameters, graph components,
  environment entities, and evaluation batches.
- `enumerate` is used when an index is part of the result or update.
- `zip` keeps related sequences aligned, especially values and weights, graph
  fields, predictions, or parameters.
- `range` represents a fixed number of steps, layers, replicas, or attempts.
- `while` is reserved for open-ended convergence, iterator draining, episode
  progression, or algorithms with an explicit termination condition.

List and dictionary comprehensions build small transformed collections. Keep a
comprehension when the mapping and optional filter fit in one readable
expression. Use a loop when it needs state changes, multiple branches, logging,
or error handling. Nested comprehensions are almost absent.

Generators are specialized for streaming or potentially large data. Dataset
batchers in [wikigraphs/wikigraphs/data/tools.py](wikigraphs/wikigraphs/data/tools.py)
and graph batchers in [ogb_lsc/pcq/batching_utils.py](ogb_lsc/pcq/batching_utils.py)
`yield` one result at a time. `yield from` delegates directly to an existing
iterator in [byol/utils/dataset.py](byol/utils/dataset.py) and similar dataset
modules. Generator state belongs to the generator instance and advances only
when the caller requests another value.

### Treat exceptions as recovery boundaries, not general branching

`try` is much rarer than `raise`: 37 `try` statements occur in 30 files across
17 projects, while 472 explicit raises occur in 163 files. This shows the normal
direction of error flow: low-level code reports invalid or impossible states;
code catches an error only where it can translate, recover, retry, terminate a
domain operation, or guarantee cleanup.

#### Scope the `try` block narrowly

Of the 37 `try` statements, 35 are inside functions and two are in guarded
module entry points. None is used as a class-body wrapper. The protected block
usually contains the specific fallible operation, not the whole caller.

Narrow scope matters because the handler then corresponds to a known failure:

- [byol/utils/checkpointing.py](byol/utils/checkpointing.py) catches
  `FileNotFoundError` around the checkpoint open or rename operation only.
- [fusion_tcv/environment.py](fusion_tcv/environment.py) catches simulator
  failures around one simulator step, then converts them into episode
  termination.
- [catch_carry/warehouse.py](catch_carry/warehouse.py) catches a failure from
  arm positioning and translates it at the environment-construction boundary.

Do not wrap a long function merely to keep it running. A broad scope can convert
an unrelated programming defect into misleading fallback behavior.

#### Use the observed recovery strategies deliberately

| Strategy | Scope and implementation | Representative example |
| --- | --- | --- |
| Missing resource becomes an optional result | Catch `FileNotFoundError` at an I/O helper and return `None` | [byol/utils/checkpointing.py](byol/utils/checkpointing.py) |
| Fast path falls back to a compatible path | Catch the failure of an optional or version-sensitive operation and execute the slower supported implementation | [compute_hfx_density.py](density_functional_approximation_dm21/density_functional_approximation_dm21/compute_hfx_density.py) |
| Iterator exhaustion becomes control state | Catch `StopIteration` directly around `next()` and mark the source complete or supply padding | [wikigraphs/wikigraphs/data/tools.py](wikigraphs/wikigraphs/data/tools.py) |
| Domain failure becomes a domain result | Catch known simulator or target exceptions and return termination or minimum reward | [fusion_tcv/environment.py](fusion_tcv/environment.py), [fusion_tcv/rewards.py](fusion_tcv/rewards.py) |
| Transient corruption is retried | Put one download attempt in `try`, break in `else`, and raise after the loop is exhausted | [ogb_lsc/pcq/download_pcq.py](ogb_lsc/pcq/download_pcq.py) |
| Exception is translated at an abstraction boundary | Catch the lower-level type and raise the type callers of the higher layer understand | [alphafold_casp13/config_dict.py](alphafold_casp13/config_dict.py), [catch_carry/warehouse.py](catch_carry/warehouse.py) |
| Interrupt triggers cleanup and propagates | Catch `KeyboardInterrupt`, shut down owned workers, then use bare `raise` | [tvt/batch_env.py](tvt/batch_env.py) |
| Cleanup or persistence must always run | Put only the main operation in `try` and cleanup/save in `finally` | [physics_inspired_models/eval_metric.py](physics_inspired_models/eval_metric.py), [ogb_lsc/pcq/experiment.py](ogb_lsc/pcq/experiment.py) |

#### Use each exception clause for its specific guarantee

- `except SomeError` runs only for the named recoverable failure. Six handlers
  catch `FileNotFoundError`; `StopIteration` and `KeyboardInterrupt` are other
  repeated protocol-level cases.
- A tuple such as `except (KeyError, ValueError)` is used when distinct library
  failures have the same meaning at the current boundary.
- `else` runs only when the protected operation succeeds. It occurs three times,
  including the download retry and reward computation examples, and keeps
  success-only work out of the catchable region.
- `finally` runs whether the operation succeeds or fails. It occurs three times
  for unconditional cancellation or checkpoint persistence.
- A bare `raise` inside a handler propagates the current exception after cleanup.
  It preserves the original traceback.

Only two handlers use bare `except`, both in old data-generation paths that log
and degrade the result. These are historical containment choices, not the
normal pattern. New code should catch `Exception` or, preferably, the narrow
types it can actually handle. Avoid swallowing `KeyboardInterrupt`,
`SystemExit`, and programmer errors.

#### Choose exception types by contract

The 472 explicit raises are dominated by a few meanings:

| Raised type | Count | Intended meaning in this repository |
| --- | ---: | --- |
| `ValueError` | 364 | Invalid value, shape, range, option, or configuration |
| `NotImplementedError` | 58 | Genuine abstract or unsupported behavior boundary |
| `RuntimeError` | 17 | Execution reached an unusable state despite valid-looking input |
| `app.UsageError` | 11 | Invalid command-line invocation |
| `KeyError` | 9 | Required named field or mapping entry is absent |

Use assertions for internal invariants, not public validation that must remain
active under optimized Python execution. Include the offending value and the
expected constraint in a raised error. When translating an exception in new
code, use explicit exception chaining where it clarifies the lower-level cause;
some historical examples predate that convention.

### Use context managers for bounded ownership and temporary state

**Widespread.** The 270 `with` statements are not limited to files. A context
manager defines a lexical region in which a resource or temporary state is
active and guarantees its exit behavior.

Observed categories include:

- File lifetime: 56 built-in `open(...)` contexts and 25 TensorFlow/gfile
  contexts close handles even on failure.
- TensorFlow graph construction: variable scopes, name scopes, control
  dependencies, device placement, graphs, and sessions are active only inside
  the indented region.
- Numerical-library state: gradient tapes, PySCF integral settings, warning
  filters, and NumPy print options are restored on exit.
- Concurrency: process pools, thread pools, and locks have bounded ownership.
- Tests: `assertRaises`, `subTest`, mock datasets, and test sessions constrain a
  temporary expectation or fixture.

Examples include file handling in [avae/checkpointer.py](avae/checkpointer.py),
graph scopes in [alphafold_casp13/contacts_network.py](alphafold_casp13/contacts_network.py),
and a multiprocessing pool in
[ogb_lsc/pcq/generate_conformer_features.py](ogb_lsc/pcq/generate_conformer_features.py).

Prefer `with` when an object exposes a context protocol. Use `try/finally` when
cleanup is required but no suitable context manager owns it.

### Classes own protocols and long-lived state

**Widespread.** Classes appear in 41 Python-bearing projects. They are used for:

- Framework modules such as Haiku, Sonnet, TensorFlow, and PyTorch networks.
- Environments, agents, tasks, rewards, and simulator wrappers.
- Iterators, readers, checkpointers, normalizers, and experiment lifecycles.
- Small structured values and enumerated modes.
- Test fixtures and parameterized suites.

Use inheritance for an actual substitutable protocol or a framework-required
base class. Abstract interfaces in [fusion_tcv/agent.py](fusion_tcv/agent.py),
[perceiver/perceiver.py](perceiver/perceiver.py), and
[physics_inspired_models/models/base.py](physics_inspired_models/models/base.py)
make required behavior explicit. `abc.abstractmethod` is used 91 times.

Properties are common—238 `@property` decorators expose computed or read-only
state without making callers depend on private representation. A property
should remain inexpensive and unsurprising; use a method for work with
significant cost or side effects.

`@classmethod` is used mainly for alternate construction or class-aware parsing.
`@staticmethod` holds behavior namespaced by a class but independent of an
instance. Ordinary instance methods remain the default when behavior uses owned
state.

### Represent structured data explicitly

**Widespread.** The repository uses `NamedTuple`, `collections.namedtuple`,
dataclasses, attrs classes, and enums instead of unlabeled tuples or magic
integers. The representation is chosen to work with the relevant framework's
tree, serialization, or transformation rules.

- Experiment state uses `NamedTuple` in
  [byol/byol_experiment.py](byol/byol_experiment.py).
- Physical references and shapes use frozen dataclasses in
  [fusion_tcv/shape.py](fusion_tcv/shape.py).
- Dataset modes and splits use enums in
  [byol/utils/dataset.py](byol/utils/dataset.py).
- Replay transitions use named records in
  [tandem_dqn/replay.py](tandem_dqn/replay.py).

Frozen dataclasses are more common than mutable dataclasses. Use immutability
for configuration and value records; use a normal state-owning class when
methods intentionally update a lifecycle.

### Use decorators at stable behavioral boundaries

Decorators execute or configure behavior at definition time, so their effect
applies to every call of the decorated function or attribute. Common groups are:

- `@property` for a read-only attribute interface.
- `@abc.abstractmethod` for a required subclass operation.
- `@dataclasses.dataclass` for generated value-record behavior.
- Framework decorators such as `jax.jit`, `jax.vmap`, `hk.transparent`, or
  Sonnet variable reuse.
- Test parameterization decorators for inputs and expected variants.
- `functools.lru_cache` for deterministic, reusable loaded data.
- `functools.wraps` in wrappers that must preserve the wrapped function's
  metadata.

Keep transformations such as `jit` at a stable computational boundary. A
decorated function should make assumptions about static arguments, side
effects, variable creation, and cache lifetime explicit.

### Use higher-order functions for assembly

**Widespread.** Callables are passed as losses, schedules, transforms, model
constructors, environment builders, and dataset operations. `functools.partial`
appears frequently to bind configuration while preserving a callable interface.
Nested named functions are preferred when logic needs several statements or a
docstring; lambdas are mainly short adapters and tree operations.

Composition is visible in reward transforms in
[fusion_tcv/rewards.py](fusion_tcv/rewards.py), model/loss factories in
[wikigraphs/utils.py](wikigraphs/utils.py), and network construction in
[tandem_dqn/networks.py](tandem_dqn/networks.py).

### Keep mutation visible and state ownership explicit

Mutation is common inside object lifecycles, data-structure construction, and
imperative environment steps. It is minimized across subsystem boundaries.

- Instance state uses private fields and is updated by lifecycle methods.
- Local lists and dictionaries are accumulated within one function and then
  returned.
- JAX parameters, optimizer state, model state, and random keys are passed and
  returned as pytrees rather than changed through globals.
- TensorFlow 1 variables are mutated through graph operations within the
  framework lifecycle.
- Module constants are treated as immutable; module-global mutation is rare.

Deleting a local name with `del` is often used to document an intentionally
unused callback argument or release a large temporary structure. It should not
be used to obscure ownership.

### Use typing and documentation where runtime structure is non-obvious

**Recurring and more common in newer projects.** Roughly one third of functions
have some annotation. Types are most useful for configuration records, nested
parameter trees, interfaces, dataset records, public arrays, and factory
callables. Dynamic tensor code remains only partially typed.

Public or non-obvious functions commonly use Google-style docstrings with
`Args:`, `Returns:`, and, when relevant, `Raises:`. Document tensor layouts,
units, semantic constraints, state changes, and side effects rather than merely
restating the signature.

### Keep parallelism at explicit outer boundaries

**Specialized.** The Python source contains no `async def`, `await`, or
`nonlocal` usage. Concurrency is introduced only where workloads are naturally
independent:

- [tvt/batch_env.py](tvt/batch_env.py) uses a `ThreadPoolExecutor` to step
  independent environments and explicitly handles interruption.
- [ogb_lsc/pcq/generate_conformer_features.py](ogb_lsc/pcq/generate_conformer_features.py)
  uses a process pool for CPU-bound conformer generation.
- [ogb_lsc/mag/datasets.py](ogb_lsc/mag/datasets.py) uses a lock around shared
  raw-array loading.
- JAX `pmap`, TensorFlow dataset parallelism, and device sharding provide
  framework-managed parallel execution.

Own executor and pool shutdown at the same layer that creates them. Keep worker
inputs serializable, avoid hidden shared mutation, and gather results in a
deterministic order when downstream behavior depends on alignment.

## Part III: API and Scientific-Computing Design

### Validate public boundaries before expensive work

**Widespread.** Constructors, parsers, configuration readers, reshape helpers,
and public numerical functions reject invalid data early.

- Raise `ValueError` for invalid values, dimensions, ranges, or combinations.
- Raise `app.UsageError` for command-line misuse.
- Validate sequence lengths, shapes, enum values, and dependent options near
  the boundary.
- Use `assert` only for an internal invariant that indicates programmer error.
- Include expected and actual values in the message.

### Make tensor and array shapes part of the contract

**Widespread.** Thirty projects explicitly check shapes. Shape-sensitive code
names batch, time, spatial, node, edge, head, channel, and feature axes; validates
ranks or compatible dimensions; and keeps padding and mask values explicit.

Return structures should have stable shapes across modes. Tests should check
both numerical values and shapes. See [perceiver/io_processors.py](perceiver/io_processors.py),
[kfac_ferminet_alpha/utils.py](kfac_ferminet_alpha/utils.py), and
[tvt/memory.py](tvt/memory.py).

### Isolate layout and representation conversions

**Recurring.** Dataset, host, device, and model layouts are converted by named
preprocessing functions instead of ad hoc transposes throughout a model.
Examples include image normalization and sharding in
[byol/utils/dataset.py](byol/utils/dataset.py), and graph batching in
[wikigraphs/wikigraphs/model/graph_net.py](wikigraphs/wikigraphs/model/graph_net.py).

### Keep mathematical helpers small and composable

**Widespread.** The median Python function is about ten lines and accepts two
arguments. Complex algorithms are decomposed into loss terms, transforms,
normalizers, schedules, masks, and update functions named after the paper's
mathematical concepts.

Use vectorized framework primitives when an operation is naturally batched.
Keep a Python loop when it more clearly expresses an environment rollout,
sequential recurrence, iterative solver, retry policy, or streaming parser.

### Handle numerical stability explicitly

**Recurring.** Probability and loss code uses clipping, epsilons, log-space
operations, masked reductions, safe normalization, and guarded division.
Constants controlling stability are named and justified. Tests cover empty
masks, zero norms, extreme logits, padding, and degenerate geometry. See
[byol/utils/helpers.py](byol/utils/helpers.py),
[gated_linear_networks](gated_linear_networks), and
[ogb_lsc/pcq/model.py](ogb_lsc/pcq/model.py).

### Treat model and optimizer state as one explicit structure

**Framework-specific to JAX and recurring elsewhere.** Parameters, optimizer
state, moving averages, random keys, and mutable network state are carried in
records or framework trees. An update accepts the current structure and returns
the next one rather than mutating unrelated globals. This makes replication,
checkpointing, and evaluation state selection visible. See
[byol/byol_experiment.py](byol/byol_experiment.py),
[wikigraphs/updaters.py](wikigraphs/updaters.py), and
[kfac_ferminet_alpha/optimizer.py](kfac_ferminet_alpha/optimizer.py).

### Separate normalization statistics from model logic

**Recurring.** Dataset normalization, online feature statistics, and output
denormalization live in dedicated functions or state-owning normalizer classes.
Training and rollout code call the same implementation so that statistics are
not recomputed inconsistently. Examples include
[meshgraphnets/normalization.py](meshgraphnets/normalization.py) and
[learning_to_simulate/learned_simulator.py](learning_to_simulate/learned_simulator.py).

### Define interfaces around interchangeable behavior

**Recurring.** Abstract classes and framework base modules define contracts for
agents, datasets, decoders, losses, position encodings, environments, rewards,
targets, and integrators. Concrete implementations remain small and
substitutable. Prefer `abc.abstractmethod`; use `NotImplementedError` only at a
genuine unsupported or abstract boundary.

### Assemble systems through composition and factories

**Widespread.** Experiments are assembled from callables, modules, transforms,
schedules, configurations, and small components. Factory functions select
architectures or construct environments once instead of spreading mode
conditionals throughout a training loop.

Examples include [fusion_tcv/rewards.py](fusion_tcv/rewards.py),
[tandem_dqn/networks.py](tandem_dqn/networks.py), and
[catch_carry/task_examples.py](catch_carry/task_examples.py).

## Part IV: Data, Training, and Experiment Lifecycles

### Centralize parsing and preprocessing

**Widespread.** Dataset modules own schema descriptions, decoding, filtering,
normalization, augmentation, batching, padding, sharding, and split selection.
Models receive documented structures rather than raw serialized records. See
[alphafold_casp13/contacts_dataset.py](alphafold_casp13/contacts_dataset.py),
[meshgraphnets/dataset.py](meshgraphnets/dataset.py), and
[rl_unplugged/atari.py](rl_unplugged/atari.py).

Training pipelines may shuffle, crop, rotate, perturb, or add noise. Evaluation
pipelines use fixed crops, ordered traversal, fixed seeds, or enumerated
transformations so results can be compared.

### Make masks, padding, and termination explicit

**Recurring.** Variable-size sequences and graphs use explicit lengths, masks,
padding values, and reset indicators. Loss functions exclude padding
deliberately. Iterators record when the input is exhausted and then drain or pad
already-loaded data. See [wikigraphs/wikigraphs/data/tools.py](wikigraphs/wikigraphs/data/tools.py),
[ogb_lsc/pcq/batching_utils.py](ogb_lsc/pcq/batching_utils.py), and
[scratchgan/utils.py](scratchgan/utils.py).

### Use framework-aware file APIs where portability requires them

**Recurring.** TensorFlow projects use `tf.io.gfile` or its compatibility form
when paths may be local or remote. Other projects use focused I/O helpers that
own encoding, compression, directory creation, and serialization. File handles
are normally opened in a context manager. See
[wikigraphs/wikigraphs/data/io_tools.py](wikigraphs/wikigraphs/data/io_tools.py)
and [cs_gan/file_utils.py](cs_gan/file_utils.py).

### Keep downloads and conversion outside model imports

**Widespread.** Large downloads and one-time preprocessing are shell scripts or
dedicated command-line programs. Importing a model does not trigger network
access or destructive conversion. New workflows should document destinations,
create directories deliberately, detect failures, and verify integrity when
practical.

### Define serialized schemas explicitly

**Recurring.** TFExample descriptions, protobuf messages, named records, and
metadata classes replace positional serialization conventions. Schema
alternatives use tagged variants such as protobuf `oneof`. See
[cadl/example.proto](cadl/example.proto) and
[sketchy/metadata_schema.py](sketchy/metadata_schema.py).

### Separate model definition, update logic, and orchestration

**Widespread.** Model modules implement forward computation. Update functions
compute losses and parameter changes. An outer experiment or loop owns
iteration, logging, evaluation cadence, and checkpoint cadence. This makes model
and loss tests possible without running a complete job.

### Make training and evaluation modes explicit

**Widespread.** Dropout, normalization, augmentation, iterator repetition, and
mutable state depend on an explicit `is_training` or mode value. Evaluation
uses deterministic preprocessing and disables training-only updates. Do not
infer mode from incidental global state.

### Return named metrics with defined reductions

**Widespread.** Losses, updates, and evaluators return dictionaries or named
records containing scalar losses, accuracies, diagnostics, and outputs. Outer
loops aggregate and log them. Metric names and reduction semantics distinguish
per-example, per-device, per-step, and global averages.

### Keep schedules pure and step-driven

**Recurring.** Learning rates, moving averages, target-network updates, and
annealing values are functions of the current step and configuration. See
[byol/utils/schedules.py](byol/utils/schedules.py),
[ogb_lsc/mag/schedules.py](ogb_lsc/mag/schedules.py), and
[adversarial_robustness/jax/utils.py](adversarial_robustness/jax/utils.py).

### Encapsulate checkpoint behavior

**Widespread in trainable projects.** Checkpoint helpers own serialization,
restoration, retention, and step metadata. Callers pass complete state rather
than save unrelated pieces independently.

- Distinguish "no checkpoint yet" from corrupt or incompatible state.
- Write through a temporary path where the project supports atomic replacement.
- Restore deliberately and log what was restored.
- Let evaluation load a specified checkpoint without starting training.
- Persist enough configuration or metadata to interpret parameters.
- Use `finally` only when saving on both success and failure is the intended
  lifecycle contract.

Examples include [byol/utils/checkpointing.py](byol/utils/checkpointing.py),
[avae/checkpointer.py](avae/checkpointer.py), and
[wikigraphs/updaters.py](wikigraphs/updaters.py).

### Make randomness explicit and reproducibility complete

**Widespread in stochastic projects.** Pass a seed, `RandomState`, or JAX PRNG
key into stochastic code. Split JAX keys where independent randomness is
required. Environment construction, dataset shuffling, augmentation,
initialization, and sampling should not accidentally share a hidden stream.

Reproduction also requires the model choice, data split, preprocessing,
optimizer, schedules, batch sizes, checkpoint source, and dependency versions.
Distinguish reduced smoke-test settings from released paper settings. See
[adversarial_robustness/jax/attacks.py](adversarial_robustness/jax/attacks.py),
[byol/utils/augmentations.py](byol/utils/augmentations.py), and
[catch_carry/task_examples.py](catch_carry/task_examples.py).

## Part V: Configuration, Executables, Logging, and Testing

### Use explicit configuration and thin Abseil entry points

**Widespread.** Executable Python modules commonly use `absl.app`, `absl.flags`,
and `absl.logging`:

1. Define flags at module scope.
2. Bind `FLAGS = flags.FLAGS` when repeatedly needed.
3. Implement `main(argv)` or `main(unused_argv)`.
4. Reject unsupported positional arguments when applicable.
5. Register required flags and multi-flag constraints.
6. Call `app.run(main)` under `if __name__ == '__main__':`.

Larger JAX projects expose `get_config()` returning an
`ml_collections.ConfigDict`. Other projects use dedicated config modules,
Sacred configuration, enums, or grouped flags. Configuration selects
components and hyperparameters; it should not hide training logic or I/O. See
[byol/configs/byol.py](byol/configs/byol.py),
[ogb_lsc/pcq/config.py](ogb_lsc/pcq/config.py), and
[physics_inspired_models/jaxline_configs.py](physics_inspired_models/jaxline_configs.py).

Run package entry points from the repository root with `python -m` when the
project follows that convention. This preserves package import behavior.

### Log at orchestration and recovery boundaries

`absl.logging` or standard logging is common in long-running programs. Log
configuration, progress, metrics, checkpoint actions, fallbacks, and recoverable
exceptions where enough context exists to act. Use `logging.exception` inside a
handler when the traceback is useful. Avoid both silently swallowing a failure
and logging the same propagated exception at every layer.

`print` remains appropriate in small demonstrations and notebooks. Structured
logging is the stronger pattern for training, evaluation, and data workflows.

### Put focused tests near the owning code

**Widespread.** Python test files use `*_test.py`; Racket tests live under
`satore/tests`. Abseil is the most common Python runner. Tests also inherit from
`parameterized.TestCase`, `tf.test.TestCase`, or `unittest.TestCase` when their
parameterization, numerical assertions, sessions, or lifecycle support is
needed.

Strong tests cover:

- Exact values for deterministic logic.
- Shapes, dtypes, and nested structures.
- Numerical agreement with a justified tolerance.
- Invalid input and the expected exception type or message.
- Boundary values, empty cases, padding, and alternative modes.
- Environment and recurrent-state transitions.

Use context managers such as `assertRaises` to limit the expected-failure scope
to the operation that should fail. Representative suites include
[fusion_tcv/transforms_test.py](fusion_tcv/transforms_test.py),
[transporter/transporter_test.py](transporter/transporter_test.py), and
[wikigraphs/wikigraphs/model/transformer_test.py](wikigraphs/wikigraphs/model/transformer_test.py).

### Add small integration and smoke paths

**Recurring.** Environment, experiment, and main-loop tests run a few steps
with tiny inputs to detect assembly failures. `run.sh` files often install a
project's requirements and launch a reduced job. These complement focused unit
tests; they do not establish paper-level model quality or localize a numerical
regression.

Examples include [byol/main_loop_test.py](byol/main_loop_test.py),
[physics_planning_games/board_games/board_games_test.py](physics_planning_games/board_games/board_games_test.py),
and [adversarial_robustness/jax/experiment_test.py](adversarial_robustness/jax/experiment_test.py).

## Part VI: Shell, Build, Notebook, and Framework Patterns

### Make shell workflows reproducible and fail visibly

**Recurring.** Run scripts use paths relative to the repository root and often
invoke Python packages with `-m`. Robust new scripts should:

- Use an appropriate shebang.
- Enable fail-fast behavior such as `set -e` and, where compatible, unset
  variable and pipeline checking.
- Quote variable expansions used as paths or arguments.
- Validate required arguments before work begins.
- Create output directories explicitly.
- Separate download, installation, preprocessing, and execution stages.
- Avoid destructive operations on unresolved or broad paths.

Existing scripts are inconsistent in strictness and quoting. Preserve behavior
when maintaining them, but use the robust pattern for new scripts.

The Travis configuration selects a project and runs its small workflow. The
DM21 Bazel build declares inputs, tests, data, generated models, and C++ AOT
outputs as explicit targets. See
[density_functional_approximation_dm21/BUILD.bazel](density_functional_approximation_dm21/BUILD.bazel).

### Use notebooks for executable exposition

**Widespread.** Notebooks combine setup, compact implementations, experiments,
plots, and interpretation. Keep cells ordered for a fresh runtime, make setup
visible, set seeds, name intermediate structures, and document shapes and units
near the relevant cell.

Move reusable or tested implementation into `.py` modules when a project has a
library surface. Avoid opaque dependence on stale cell state. Notebook-backed
libraries include [Enformer](enformer) and [Perceiver](perceiver), while
[causal_reasoning](causal_reasoning) and [powerpropagation](powerpropagation)
are notebook-centered releases.

### JAX, Haiku, Optax, and JAXline

**Framework-specific.** Common implementation patterns are:

- Pure forward and loss functions with explicit parameters and state.
- Haiku modules transformed into `init` and `apply` functions.
- PRNG keys split at each independent random operation.
- Optax transformations for optimizer state and parameter updates.
- `jit`, `vmap`, and `pmap` around stable computational boundaries.
- Pytrees for parameters, state, batches, and multi-device replication.
- JAXline `Experiment` classes for initialization, stepping, evaluation, and
  checkpoint interaction.
- Explicit device/NumPy conversion at system boundaries.

Do not perform untracked Python side effects inside transformed functions. Keep
array shapes and static arguments stable across compiled calls. Examples include
[adversarial_robustness/jax](adversarial_robustness/jax), [nfnets](nfnets),
[perceiver](perceiver), and [ogb_lsc](ogb_lsc).

### TensorFlow and Sonnet

The repository contains two generations:

- TensorFlow 1 and Sonnet 1 use graphs, placeholders, sessions, variable scopes,
  collections, control dependencies, and explicit `is_training` values.
- TensorFlow 2 and Sonnet 2 favor eager-compatible modules, `tf.data`,
  `tf.function` where useful, gradient tapes, and object-based state.

Stay within the generation selected by the project. A TensorFlow `with` block
often establishes graph construction or execution context rather than ordinary
resource lifetime. Compatibility imports are migration boundaries, not a reason
to mix execution models casually. See [cs_gan](cs_gan), [tvt](tvt), and
[enformer](enformer).

### Reinforcement-learning environments and Composer tasks

Projects using `dm_env`, Pycolab, or Control Suite commonly expose `reset()`,
`step(action)`, observation specs, and action specs; return structured
timesteps; separate tasks from agents; wrap environments for preprocessing or
automatic reset; and test episode boundaries.

[box_arrangement](box_arrangement), [catch_carry](catch_carry), and
[physics_planning_games](physics_planning_games) separate reusable entities and
props from task logic. Builder functions assemble arenas, walkers, rewards,
observations, and randomization. Simulator exceptions are caught at the
environment boundary only when they have a defined episode-level meaning.

## Part VII: Language-Specific Practices Beyond Python

### Racket in Satore

The [satore](satore) project uses language-native modular patterns:

- `require` and `provide` define dependencies and public surfaces.
- Structures represent logical values and indexed data.
- Small functions implement unification, rewriting, tries, clauses, and
  saturation.
- Macros encapsulate repeated language and instrumentation patterns.
- Mutating operations make state changes visible.
- RackUnit covers exact behavior, failure, and stress cases.
- `module+ main`, `module+ test`, and `module+ drracket` isolate executable,
  test, and interactive scopes from normal imports.

Racket's equivalent recovery boundary is `with-handlers`. It is used narrowly
in [satore/interact.rkt](satore/interact.rkt) to handle interactive failures and
in [satore/tptp.rkt](satore/tptp.rkt) to add input context before re-raising.
Keep these idioms Racket-native rather than translating Python structure
literally.

### Lua in DeepMind Lab tasks

The [tvt/dmlab](tvt/dmlab) modules expose a `createLevelApi(kwargs)` factory.
The returned table implements engine callbacks such as `init`, `start`,
`nextMap`, pickup handling, and episode termination. Dependencies and constants
are local, `DEFAULTS` tables collect configuration, private helpers build task
phases, and thin scenario modules configure a shared factory.

These modules do not use `pcall` or `xpcall`; invalid factory inputs are checked
with `assert` where required by the scenario. Keep callbacks consistent with the
engine contract and configuration out of the reusable factory.

### Protobuf schemas in CADL

The [cadl](cadl) schemas use `proto3` packages, explicit imports, stable numeric
field tags, nested messages, `oneof` for alternatives, `repeated` fields for
sequences, and custom options for domain constraints. Add fields with new tags
and never reuse an existing tag for a different meaning.

### C++ in DM21

The small [DM21 C++ surface](density_functional_approximation_dm21/cc) uses
header guards, separate declarations and definitions, `constexpr` dimensions,
conditional compilation for optional XLA support, and explicit status checking
after generated-code invocation. It does not use C++ `try`/`catch`; the returned
status is checked in an `if` branch. Comments connect flattened buffers to the
Python tensor shapes expected by the generated model.

## Historical and Inconsistent Patterns

The following exist but should not be elevated into repository-wide rules:

- Test coverage is publication-dependent; many dataset and notebook releases
  have no automated tests.
- Annotation coverage varies by age and framework.
- Some projects are installable while others run only from the repository root.
- Dependency constraints range from exact pins to minimum versions and VCS
  commits.
- Shell scripts vary in strictness, quoting, temporary-directory hygiene, and
  download verification.
- Older projects use `six`, `__future__`, TensorFlow 1 sessions, and Sonnet 1.
- Two Python handlers use bare `except`; they are containment exceptions, not a
  pattern for new code.
- A few large notebook cells and functions favor publication fidelity over
  reusable structure.
- `print` is common in demos; structured logging is more common in trainable
  command-line systems.
- Assertions are widespread for internal scientific invariants but cannot
  replace public validation.

When maintaining an existing project, preserve its execution model and public
behavior. When adding new code, follow the strongest applicable recurring
practice rather than copying the weakest historical example.

## Practical Decision Guide

When choosing an implementation construct, use these repository-derived rules:

| Need | Preferred construct and scope |
| --- | --- |
| Pure transformation or reusable calculation | Module-level function |
| Behavior that owns lifecycle state | Method with private instance fields |
| One local callback configured by its creator | Nested function or short lambda |
| Fixed traversal | `for`, using `enumerate` or `zip` when alignment is explicit |
| Streaming or lazy batching | Generator with `yield` |
| Validation failure | Raise a specific exception at the public boundary |
| Recoverable external failure | Narrow `try` around the fallible operation |
| Success-only work after a risky operation | `try`/`except`/`else` |
| Cleanup that must always happen | Context manager or `try`/`finally` |
| Temporary framework state | Framework context manager |
| Alternative implementations | Factory or abstract interface |
| Immutable structured value | Named tuple, frozen dataclass, or enum |
| Parallel independent work | Explicit pool/executor or framework parallel primitive |

## Contribution Checklist

Before submitting a change, check that:

- The change stays within the owning publication or subsystem boundary.
- New source files contain the correct license header and module documentation.
- Naming, two-space indentation, and line length match surrounding code.
- Imports have no unnecessary side effects and dependencies remain project-local.
- Function and object scopes give state a clear owner.
- Public inputs, configuration, shapes, and error cases are explicit.
- A `try` block protects only the operation whose failure is understood.
- Handlers catch only errors they can recover from, translate, or deliberately
  convert into a domain result.
- Cleanup uses a context manager or `finally`; propagated failures retain their
  useful traceback.
- Loops, comprehensions, and generators match the size and statefulness of the
  data flow.
- Randomness and mutable model state have explicit owners.
- Model, dataset, training, evaluation, and I/O responsibilities remain
  separated.
- Dependency changes preserve a coherent framework version set.
- Tests cover values, shapes, structures, invalid inputs, and relevant numerical
  tolerances.
- A small integration path verifies assembly when multiple components change.
- The README and runnable commands remain accurate.
- Historical compatibility code has not been modernized without testing the
  complete affected workflow.
- The change follows the review process in
  [CONTRIBUTING.md](CONTRIBUTING.md).
