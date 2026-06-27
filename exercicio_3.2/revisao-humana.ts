import { app, HttpRequest, HttpResponseInit } from '@azure/functions';

export async function feedbackHandler(
  request: HttpRequest
): Promise<HttpResponseInit> {
  const body = await request.json() as any; // não usar any

  const feedback = {
    queryId: body.queryId,
    rating: body.rating,
    comment: body.comment,
    attendantEmail: body.attendantEmail,
    timestamp: new Date().toISOString()
  }; // usar zod.object().strict()

  console.log('Feedback recebido:', JSON.stringify(feedback)); // usar pino ao invez de log, não logar dados sensiveis (está sendo logado todo o objeto e expondo informações sensiveis)

  const { CosmosClient } = require('@azure/cosmos'); // realizar import no topo
  const client = new CosmosClient(process.env.COSMOS_CONNECTION_STRING);
  const database = client.database('novatech');
  const container = database.container('feedbacks');

  await container.items.create(feedback);

  return { status: 200, body: 'OK' };
}

app.http('feedback', {
  methods: ['POST'],
  handler: feedbackHandler
});