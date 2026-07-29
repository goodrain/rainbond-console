# MCP Client Package Upload Implementation Spec

## Outcome

Local package-backed deployments must stream the client file to Rainbond Console before component creation. RainSkills must no longer discover the two MCP tools that read paths from the Console filesystem, while generic MCP clients and direct callers retain compatibility.

## Contract

`rainbond_init_package_upload` keeps `upload_url` and adds:

```json
{
  "upload_request": {
    "method": "POST",
    "url": "/console/regions/<region>/websocket/package_build/component/events/<event>",
    "url_scope": "console_origin",
    "content_type": "multipart/form-data",
    "file_field": "packageTarFile",
    "authorization": "none"
  }
}
```

RainSkills consumes every field explicitly. It resolves `url` against `RAINBOND_URL`, requires the exact same HTTP(S) origin, and invokes `curl` with an argument array. It never places package bytes or credentials in MCP JSON.

## Discovery Compatibility

In `deployment_invocation_context("rainskills", "codex")` and `deployment_invocation_context("rainskills", "claude_code")`, `tools/list` omits:

- `rainbond_upload_package_file`
- `rainbond_create_component_from_local_package`

The generic MCP list still includes both names. `call_tool` dispatch and schemas remain intact, including within a RainSkills context when a caller already knows the legacy name.

## Client Flow

```text
helper prepare
  -> MCP init upload
  -> helper upload with upload_request
  -> helper cleanup generated archive
  -> MCP status (uploaded_packages must be non-empty)
  -> MCP create component from event_id
```

On init failure, clean only the generated local archive. On HTTP failure, clean the local archive and then delete the remote event. On empty upload status, delete the remote event and do not create a component. Never delete an original package supplied by the user.

## Commit Groups

1. `rainbond-console`: `fix: expose MCP client package upload contract`
   - TDD the response contract.
   - TDD RainSkills-only discovery filtering and direct-call compatibility.
   - Update tool description and test manifest.
   - Run focused tests, formatting, and `make check`.

2. `rainskills`: `fix: upload local packages through Console`
   - TDD a dependency-free Python prepare/upload/cleanup helper.
   - Update package-backed skill guidance and evals.
   - Wire helper and package-content tests into `npm test`.
   - Run evals, packaging tests, and full test suite under Node 24.

3. Run cross-repository API compatibility review, extract unexpected issues, and complete both branches only after verification evidence is current.

The executable task details, commands, code sketches, and acceptance criteria are in `mcp-client-package-upload.yaml`.
