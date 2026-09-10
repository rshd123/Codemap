#!/usr/bin/env python3
"""Seed CodeMap Neo4j with a mock dependency graph for UI testing."""

from neo4j import GraphDatabase

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"

SEED_CYPHER = """
// --- Packages ---
MERGE (p1:Package {name: 'express', version: '4.18.2', ecosystem: 'npm'})
MERGE (p2:Package {name: 'lodash', version: '4.17.21', ecosystem: 'npm'})
MERGE (p3:Package {name: 'body-parser', version: '1.20.1', ecosystem: 'npm'})
MERGE (p4:Package {name: 'cookie-parser', version: '1.4.6', ecosystem: 'npm'})
MERGE (p5:Package {name: 'cors', version: '2.8.5', ecosystem: 'npm'})
MERGE (p6:Package {name: 'helmet', version: '7.1.0', ecosystem: 'npm'})
MERGE (p7:Package {name: 'morgan', version: '1.10.0', ecosystem: 'npm'})
MERGE (p8:Package {name: 'axios', version: '1.6.2', ecosystem: 'npm'})
MERGE (p9:Package {name: 'react', version: '18.2.0', ecosystem: 'npm'})
MERGE (p10:Package {name: 'react-dom', version: '18.2.0', ecosystem: 'npm'})

// --- Vulnerability ---
MERGE (v1:Vulnerability {id: 'CVE-2024-12345', cvss: 8.6, summary: 'Prototype pollution in lodash < 4.17.22', source: 'NVD'})

// --- Issues ---
MERGE (i1:Issue {id: 'GH-101', title: 'Fix prototype pollution in merge functions', status: 'closed', url: 'https://github.com/example/repo/issues/101'})
MERGE (i2:Issue {id: 'GH-102', title: 'Upgrade lodash to patched version', status: 'closed', url: 'https://github.com/example/repo/issues/102'})

// --- Commits ---
MERGE (c1:Commit {hash: 'a1b2c3d', message: 'fix: patch prototype pollution in lodash merge', timestamp: '2024-03-15T10:30:00Z', author: 'dev@example.com'})
MERGE (c2:Commit {hash: 'e4f5g6h', message: 'chore: bump lodash to 4.17.22', timestamp: '2024-03-16T14:00:00Z', author: 'dev@example.com'})

// --- Dependency relationships ---
MERGE (p1)-[:DEPENDS_ON]->(p2)
MERGE (p1)-[:DEPENDS_ON]->(p3)
MERGE (p1)-[:DEPENDS_ON]->(p4)
MERGE (p1)-[:DEPENDS_ON]->(p5)
MERGE (p1)-[:DEPENDS_ON]->(p6)
MERGE (p1)-[:DEPENDS_ON]->(p7)
MERGE (p9)-[:DEPENDS_ON]->(p10)
MERGE (p8)-[:DEPENDS_ON]->(p2)

// --- Vulnerability relationships ---
MERGE (v1)-[:AFFECTS]->(p2)

// --- Fix relationships ---
MERGE (c1)-[:FIXES]->(i1)
MERGE (c2)-[:FIXES]->(i2)
MERGE (c1)-[:PATCHES]->(v1)
MERGE (c2)-[:PATCHES]->(v1)

// --- Issue references ---
MERGE (i1)-[:REFERENCES]->(v1)
MERGE (i2)-[:REFERENCES]->(v1)
"""


def seed():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
        session.run(SEED_CYPHER)
        result = session.run("MATCH (n) RETURN labels(n)[0] AS label, count(*) AS count")
        for record in result:
            print(f"  {record['label']}: {record['count']}")
    driver.close()
    print("Seed complete.")


if __name__ == "__main__":
    seed()
