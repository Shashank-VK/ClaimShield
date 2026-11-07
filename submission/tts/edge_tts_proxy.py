#!/usr/bin/env python3
"""Edge TTS via the VM's mandatory proxy, trusting the egress CA bundle."""
import asyncio
import os
import ssl
import sys

import aiohttp
import edge_tts
import edge_tts.communicate as _comm

PROXY = os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY") or os.environ.get("http_proxy") or os.environ.get("HTTP_PROXY")
CA = os.environ.get("SSL_CERT_FILE", "/run/hatch/egress-tls/ca-bundle.pem")


async def main():
    voice, text_file, out = sys.argv[1], sys.argv[2], sys.argv[3]
    text = open(text_file).read()
    ctx = ssl.create_default_context(cafile=CA)
    _comm._SSL_CTX = ctx  # edge-tts forces its own ctx on ws_connect; override it
    connector = aiohttp.TCPConnector(ssl=ctx)
    comm = edge_tts.Communicate(text, voice, proxy=PROXY, connector=connector)
    await comm.save(out)
    print("OK", out)


asyncio.run(main())
