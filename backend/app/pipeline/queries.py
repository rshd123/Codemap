"""Parameterized Cypher write templates shared by every ingestion source.

Every template reads its values from `row.*` and is executed through
`app.pipeline.base.write_rows`, which wraps it in `UNWIND $rows AS row`.
No caller-supplied text is ever interpolated into these strings.
"""

VULN_UPSERT = """
MERGE (v:Vulnerability {id: row.id})
ON CREATE SET v.created = timestamp(), v.updated = timestamp(), v.source = row.source,
              v.summary = row.summary, v.cvss = row.cvss, v.cvss_vector = row.cvss_vector,
              v.severity = row.severity, v.published = row.published, v.modified = row.modified,
              v.aliases = row.aliases, v.reference_urls = row.reference_urls,
              v.cwe = row.cwe, v.osv_id = row.osv_id, v.cve_id = row.cve_id, v.url = row.url
ON MATCH SET v.updated = timestamp(),
             v.summary = coalesce(row.summary, v.summary),
             v.cvss = coalesce(row.cvss, v.cvss),
             v.cvss_vector = coalesce(row.cvss_vector, v.cvss_vector),
             v.severity = coalesce(row.severity, v.severity),
             v.published = coalesce(row.published, v.published),
             v.modified = coalesce(row.modified, v.modified),
             v.aliases = coalesce(row.aliases, v.aliases),
             v.reference_urls = coalesce(row.reference_urls, v.reference_urls),
             v.cwe = coalesce(row.cwe, v.cwe),
             v.osv_id = coalesce(row.osv_id, v.osv_id),
             v.cve_id = coalesce(row.cve_id, v.cve_id),
             v.url = coalesce(row.url, v.url),
             v.source = CASE
                 WHEN v.source IS NULL THEN row.source
                 WHEN v.source = row.source THEN v.source
                 ELSE v.source + '+' + row.source
             END
"""

AFFECTS_UPSERT = """
MATCH (v:Vulnerability {id: row.vuln_id})
MERGE (p:Package {name: row.name, ecosystem: row.ecosystem})
ON CREATE SET p.created = timestamp(), p.updated = timestamp(), p.version = row.version,
              p.source = row.source
ON MATCH SET p.updated = timestamp(), p.version = coalesce(row.version, p.version)
MERGE (v)-[r:AFFECTS]->(p)
ON CREATE SET r.created = timestamp(), r.updated = timestamp(), r.versions = row.versions,
              r.fixed_versions = row.fixed_versions, r.version_range = row.version_range
ON MATCH SET r.updated = timestamp(),
             r.versions = coalesce(row.versions, r.versions),
             r.fixed_versions = coalesce(row.fixed_versions, r.fixed_versions),
             r.version_range = coalesce(row.version_range, r.version_range)
"""

PACKAGE_UPSERT = """
MERGE (p:Package {name: row.name, ecosystem: row.ecosystem})
ON CREATE SET p.created = timestamp(), p.updated = timestamp(), p.version = row.version,
              p.repo = row.repo, p.url = row.url, p.description = row.description,
              p.source = row.source, p.stars = row.stars
ON MATCH SET p.updated = timestamp(),
             p.version = coalesce(row.version, p.version),
             p.repo = coalesce(row.repo, p.repo),
             p.url = coalesce(row.url, p.url),
             p.description = coalesce(row.description, p.description),
             p.stars = coalesce(row.stars, p.stars),
             p.source = CASE
                 WHEN p.source IS NULL THEN row.source
                 WHEN p.source = row.source THEN p.source
                 ELSE p.source + '+' + row.source
             END
"""

DEPENDS_ON_UPSERT = """
MATCH (a:Package {name: row.from_name, ecosystem: row.from_ecosystem})
MERGE (b:Package {name: row.to_name, ecosystem: row.to_ecosystem})
ON CREATE SET b.created = timestamp(), b.updated = timestamp(), b.version = row.to_version,
              b.source = row.source
ON MATCH SET b.updated = timestamp(), b.version = coalesce(row.to_version, b.version)
MERGE (a)-[r:DEPENDS_ON]->(b)
ON CREATE SET r.created = timestamp(), r.updated = timestamp(), r.spec = row.spec, r.kind = row.kind
ON MATCH SET r.updated = timestamp(), r.spec = coalesce(row.spec, r.spec), r.kind = coalesce(row.kind, r.kind)
"""

ISSUE_UPSERT = """
MERGE (i:Issue {id: row.id})
ON CREATE SET i.created = timestamp(), i.updated = timestamp(), i.title = row.title,
              i.status = row.status, i.url = row.url, i.repo = row.repo, i.number = row.number,
              i.author = row.author, i.created_at = row.created_at, i.source = row.source
ON MATCH SET i.updated = timestamp(),
             i.title = coalesce(row.title, i.title),
             i.status = coalesce(row.status, i.status),
             i.url = coalesce(row.url, i.url),
             i.repo = coalesce(row.repo, i.repo),
             i.number = coalesce(row.number, i.number),
             i.author = coalesce(row.author, i.author),
             i.created_at = coalesce(row.created_at, i.created_at),
             i.source = CASE
                 WHEN i.source IS NULL THEN row.source
                 WHEN i.source = row.source THEN i.source
                 ELSE i.source + '+' + row.source
             END
"""

COMMIT_UPSERT = """
MERGE (c:Commit {hash: row.hash})
ON CREATE SET c.created = timestamp(), c.updated = timestamp(), c.message = row.message,
              c.timestamp = row.timestamp, c.author = row.author, c.repo = row.repo,
              c.url = row.url, c.source = row.source
ON MATCH SET c.updated = timestamp(),
             c.message = coalesce(row.message, c.message),
             c.timestamp = coalesce(row.timestamp, c.timestamp),
             c.author = coalesce(row.author, c.author),
             c.repo = coalesce(row.repo, c.repo),
             c.url = coalesce(row.url, c.url)
"""

FIXES_LINK = """
MATCH (c:Commit {hash: row.hash})
MATCH (i:Issue {id: row.issue_id})
MERGE (c)-[r:FIXES]->(i)
ON CREATE SET r.created = timestamp(), r.source = row.source
"""

PATCHES_LINK = """
MATCH (c:Commit {hash: row.hash})
MATCH (v:Vulnerability {id: row.vuln_id})
MERGE (c)-[r:PATCHES]->(v)
ON CREATE SET r.created = timestamp(), r.source = row.source
"""

REFERENCES_LINK = """
MATCH (i:Issue {id: row.issue_id})
MERGE (v:Vulnerability {id: row.vuln_id})
ON CREATE SET v.created = timestamp(), v.updated = timestamp(), v.source = row.source,
              v.summary = row.summary, v.url = row.url, v.aliases = row.aliases,
              v.cve_id = row.cve_id, v.reference_urls = row.reference_urls
ON MATCH SET v.updated = timestamp(),
             v.summary = coalesce(v.summary, row.summary),
             v.aliases = coalesce(row.aliases, v.aliases),
             v.cve_id = coalesce(row.cve_id, v.cve_id),
             v.url = coalesce(v.url, row.url),
             v.source = CASE
                 WHEN v.source IS NULL THEN row.source
                 WHEN v.source = row.source THEN v.source
                 ELSE v.source + '+' + row.source
             END
MERGE (i)-[r:REFERENCES]->(v)
ON CREATE SET r.created = timestamp(), r.source = row.source
"""
