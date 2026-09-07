const pythonService = require('../config/pythonService');

exports.handleQuery = async (req, res) => {
  try {
    const { prompt } = req.body;
    const response = await pythonService.post('/query', { prompt });
    res.json(response.data);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};
