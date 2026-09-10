# AI Engine prerequisite contract

`skills-prerequisites-v1.json` is copied without modification from
`rainbond-ai-engine/contracts/skills-prerequisites-v1.json` at commit
`c73d1af37226c901e1a3c0a1febe53f2dbdd205f`.

Console unit tests use this pinned contract so a standalone checkout does not
require a sibling AI Engine repository. When updating the supported upstream
contract, refresh this file from the corresponding upstream commit and update
the revision above.

Set `RAINBOND_AI_ENGINE_ROOT` explicitly to test against an upstream checkout
instead. An invalid explicit path fails the test rather than falling back to
the fixture.
