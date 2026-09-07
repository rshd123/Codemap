const driver = require('../config/neo4j');

exports.getGraph = async (req, res) => {
  const session = driver.session();
  try {
    const result = await session.run('MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 100');
    const nodes = [];
    const edges = [];
    result.records.forEach(record => {
      const n = record.get('n');
      const m = record.get('m');
      const r = record.get('r');
      nodes.push({ id: n.identity.toString(), label: n.labels[0], properties: n.properties });
      nodes.push({ id: m.identity.toString(), label: m.labels[0], properties: m.properties });
      edges.push({ source: r.startNodeIdentity.toString(), target: r.endNodeIdentity.toString(), type: r.type });
    });
    res.json({ nodes, edges });
  } catch (error) {
    res.status(500).json({ error: error.message });
  } finally {
    await session.close();
  }
};
