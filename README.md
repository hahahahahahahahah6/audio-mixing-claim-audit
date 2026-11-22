# Documentation claim auditor

This offline static auditor compares documented capability claims with Python source evidence. It never executes inspected code.

## Usage

```sh
PIP_NO_CACHE_DIR=1 python3 -m pip install .
audio-mixing-claim-audit audit . --json
python3 -m audio_mixing_claim_audit audit . --verbose
```

The path defaults to the current directory. Repeat `--ignore PREFIX` to exclude paths. Use `--fail-on medium` to include test-only findings. Exit status is 0 for PASS, 2 for findings at the chosen threshold, and 1 for usage or I/O errors. Use `--version` to show the version.

Finding identifiers:

```text
documented-audio-mixing-claim-false
documented-no-audio-mixing-claim-false
```

## Differentiation

Other families cover synthesising new sound from content or models, splitting a mix into stems, transcribing speech, turning text into speech, removing noise from one track, composing music, turning audio into notation, and editing video. These are outside this audit.

Other excluded families cover spreadsheet reading and generation, word-document reading and generation, presentation reading and generation, PDF extraction, generation, merging, splitting, encryption, rotation, form-filling, watermarking, redaction, compression and annotation, table extraction, OCR, document extraction, e-signature, payment processing, screen recording, video generation, QR code generation, barcode generation, and barcode scanning.

## Limitations

- This phrase may refer to a roadmap feature:

  ```text
  audio mixing
  ```

- This phrase may refer to a person or a hardware desk:

  ```text
  audio mixer
  ```

- This phrase may describe a test fixture or unshipped sample:

  ```text
  mix audio
  ```

- This phrase may refer to metadata or a file with its transcript:

  ```text
  combine audio
  ```

- This phrase may refer to keeping channels separate in a multichannel stream:

  ```text
  merge audio
  ```

- This phrase may refer to a crossfade between sequential tracks:

  ```text
  blend audio
  ```

- This phrase may refer to stacking timeline tracks without summing them:

  ```text
  layer audio
  ```

- This phrase may refer to placing a voiceover on a video timeline:

  ```text
  overlay audio
  ```

- This phrase may refer to a DJ playlist:

  ```text
  mix tracks
  ```

- The segment pair accepts an overlay method on an unrelated object.
- The segment pair does not trace whether the method acts on the loaded segment.
- A variable holding a combine type is missed, even when its value is suitable.
- The combiner pair does not trace whether the build call acts on the constructed object.
- A filter graph counts even if it never runs.
- The alternate filter method is accepted alongside the primary name.
- A clip composition counts even if its clips never overlap.
- A bare library import is not evidence.
- Roadmap, changelog, and TODO prose still counts as a claim.
- A denial outside the list is not recognised and a positive phrase may still count.
- Documents outside the root README and directories named docs are not read.
- Evidence split across modules is missed.
- A locally defined route name shadows the route, including wrappers.
- Dead code counts as evidence.
- Subprocess commands invoking external tools are not evidence.
- Source separation alone is not evidence.
- Sound synthesis alone is not evidence.
- A locally defined generic name is shadowed.
- Alias chains the tracer cannot follow are missed.
- Exact phrases are matched without semantic interpretation.
- Implementations in other languages are invisible.
- Runtime-only routes are invisible because code is not executed and the network is not accessed.
- The segment construction or load and overlay call must be in one module.
- The combiner construction and suitable literal must be in one module.
- A channel-merging filter is not evidence.
- An append call is not evidence.
- A sequential clip concatenation call is not evidence.
- A sequential filter call is not evidence.
- A segment construction or load alone is not evidence.
- An overlay call alone is not evidence.
- A combiner construction alone is not evidence.
- A build call alone is not evidence.
- Speech recognition alone is not evidence.
- Array arithmetic alone is not evidence.
- Static matching does not establish correctness.
