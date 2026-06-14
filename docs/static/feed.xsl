<?xml version="1.0" encoding="UTF-8"?>
<!--
  Browser-only stylesheet for the JCStream RSS feeds.
  Real RSS readers ignore xml-stylesheet directives entirely, so they see
  the raw RSS 2.0 markup. Browsers that don't ship a feed UI (Chrome since
  76, all post-Quantum Firefox, Safari) apply this XSLT and render a
  human-readable HTML page.
-->
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:atom="http://www.w3.org/2005/Atom">
  <xsl:output method="html" version="1.0" encoding="UTF-8" indent="yes"/>
  <xsl:template match="/">
    <html lang="en">
      <head>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1"/>
        <title><xsl:value-of select="rss/channel/title"/> &#183; RSS feed</title>
        <meta name="robots" content="noindex, noarchive"/>
        <style>
          :root { color-scheme: light; }
          html { background: #fafaf8; }
          body { font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
                 color: #1a1d23; max-width: 920px; margin: 0 auto;
                 padding: 32px 24px 64px; line-height: 1.5; }
          .banner { background: #fff7e6; border: 1px solid #ffd699;
                    border-radius: 6px; padding: 10px 14px; font-size: 13px;
                    color: #664400; margin-bottom: 28px; }
          .banner code { background: rgba(0,0,0,0.05); padding: 1px 4px;
                         border-radius: 3px; font-size: 12px; }
          h1 { margin: 0 0 4px; font-size: 24px; letter-spacing: -0.02em; }
          .channel-meta { color: #475569; font-size: 14px; margin: 0 0 28px; }
          .item { background: #fff; border: 1px solid #e6e3dc; border-radius: 8px;
                  padding: 14px 18px; margin: 0 0 12px; }
          .item-title { margin: 0 0 6px; font-size: 16px; font-weight: 600;
                        letter-spacing: -0.01em; }
          .item-title a { color: #1a1d23; text-decoration: none; }
          .item-title a:hover { color: #3354ad; text-decoration: underline; }
          .item-meta { font-size: 12px; color: #64748b; margin: 0 0 8px;
                       font-variant-numeric: tabular-nums; }
          .item-meta .cat { display: inline-block; padding: 1px 7px;
                            background: #f4f3ef; border-radius: 999px;
                            font-weight: 600; color: #475569;
                            margin-right: 6px; font-size: 11px; }
          .item-desc { font-size: 14px; color: #334155; margin: 0; }
          footer { margin-top: 36px; padding-top: 16px; border-top: 1px solid #e6e3dc;
                   font-size: 13px; color: #64748b; }
          footer a { color: #3354ad; }
        </style>
      </head>
      <body>
        <p class="banner">
          <strong>This is a machine-readable RSS feed.</strong>
          You can subscribe to it in any feed reader (NetNewsWire, Feedly,
          Miniflux, Thunderbird, Inoreader). Browsers don't have a built-in
          feed UI any more, so what you see below is a styled rendering of
          the same XML. Copy the URL <code><xsl:value-of select="rss/channel/atom:link/@href"/></code>
          into your reader to subscribe.
        </p>
        <h1><xsl:value-of select="rss/channel/title"/></h1>
        <p class="channel-meta">
          <xsl:value-of select="rss/channel/description"/>
          <xsl:if test="rss/channel/lastBuildDate">
            &#160;&#183; updated <xsl:value-of select="rss/channel/lastBuildDate"/>
          </xsl:if>
        </p>

        <xsl:for-each select="rss/channel/item">
          <article class="item">
            <h2 class="item-title">
              <a>
                <xsl:attribute name="href"><xsl:value-of select="link"/></xsl:attribute>
                <xsl:value-of select="title"/>
              </a>
            </h2>
            <p class="item-meta">
              <xsl:if test="category">
                <span class="cat"><xsl:value-of select="category"/></span>
              </xsl:if>
              <xsl:value-of select="pubDate"/>
            </p>
            <p class="item-desc"><xsl:value-of select="description"/></p>
          </article>
        </xsl:for-each>

        <footer>
          &#169; JCStream &#183;
          <a href="/">homepage</a> &#183;
          <a href="/data/">data &amp; methodology</a> &#183;
          <a href="/feed.xml">all changes feed</a> &#183;
          <a href="/booked.xml">bookings only</a> &#183;
          <a href="/released.xml">releases only</a>
        </footer>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>
