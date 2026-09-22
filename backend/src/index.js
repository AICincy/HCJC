// JCStream backend.
//
// The published site stays static. This service is the only component in the
// repository that talks to Supabase, and it is the only place a Supabase
// credential is read. See `../README.md` for the env contract and
// `.env.example` for local values.
//
// Scope note: this file scaffolds credential verification only. It defines no
// tables and no product routes. Add those as a separate, named task.

import { createServer } from 'node:http'
import { Readable } from 'node:stream'

import { withSupabase } from '@supabase/server'

const HOST = process.env.HOST ?? '0.0.0.0'
const PORT = Number(process.env.PORT ?? 8787)

// Each route carries its own auth mode. `auth: 'user'` verifies the caller's
// JWT against the project JWKS before the handler runs; `auth: 'none'` accepts
// unauthenticated requests. Never widen a mode to make a client work.
const routes = {
  'GET /health': withSupabase({ auth: 'none' }, async () =>
    Response.json({ ok: true }),
  ),

  // Echoes the verified identity. Touches no table, so it is safe to expose
  // before any schema exists and it proves the JWKS path end to end.
  'GET /me': withSupabase({ auth: 'user' }, async (_req, ctx) =>
    Response.json({ authMode: ctx.authMode, claims: ctx.userClaims }),
  ),
}

// Bridges Node's IncomingMessage into the Fetch API Request that
// `@supabase/server` handlers (and the platform they target) expect.
function toRequest(req) {
  const origin = `http://${req.headers.host ?? `${HOST}:${PORT}`}`
  const url = new URL(req.url ?? '/', origin)

  const headers = new Headers()
  for (const [key, value] of Object.entries(req.headers)) {
    if (Array.isArray(value)) value.forEach((item) => headers.append(key, item))
    else if (value !== undefined) headers.set(key, value)
  }

  const method = req.method ?? 'GET'
  const bodyless = method === 'GET' || method === 'HEAD'

  return new Request(url, {
    method,
    headers,
    body: bodyless ? undefined : Readable.toWeb(req),
    // Required by the Fetch spec when streaming a request body.
    duplex: bodyless ? undefined : 'half',
  })
}

async function toNodeResponse(res, response) {
  const headers = {}
  for (const [key, value] of response.headers) headers[key] = value
  // `set-cookie` is the one header that legitimately repeats.
  const cookies = response.headers.getSetCookie?.() ?? []
  if (cookies.length > 0) headers['set-cookie'] = cookies

  res.writeHead(response.status, headers)

  if (!response.body) {
    res.end()
    return
  }

  for await (const chunk of Readable.fromWeb(response.body)) res.write(chunk)
  res.end()
}

const server = createServer(async (req, res) => {
  try {
    const handler = routes[`${req.method} ${new URL(req.url ?? '/', 'http://localhost').pathname}`]

    if (!handler) {
      res.writeHead(404, { 'content-type': 'application/json' })
      res.end(JSON.stringify({ error: 'not_found' }))
      return
    }

    await toNodeResponse(res, await handler(toRequest(req)))
  } catch (error) {
    // Never echo the underlying message: credential and JWKS errors from
    // @supabase/server can carry upstream response detail.
    //
    // The URL is attacker-controlled, so it is passed as an argument rather
    // than interpolated into the format string, and newlines are stripped so a
    // crafted request cannot forge extra log lines. Only the first argument to
    // console.error is treated as a format string.
    const safeUrl = String(req.url ?? '').replace(/[\r\n]+/g, '')
    console.error('unhandled error on', req.method, safeUrl, error)
    if (!res.headersSent) res.writeHead(500, { 'content-type': 'application/json' })
    res.end(JSON.stringify({ error: 'internal_error' }))
  }
})

server.listen(PORT, HOST, () => {
  console.log(`jcstream backend listening on http://${HOST}:${PORT}`)
})
