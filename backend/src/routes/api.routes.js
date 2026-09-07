const express = require('express');
const router = express.Router();
const queryController = require('../controllers/query.controller');
const graphController = require('../controllers/graph.controller');

router.post('/query', queryController.handleQuery);
router.get('/graph', graphController.getGraph);

module.exports = router;
