# Backend API Contract

## Tactical Analysis Request

`POST /api/v1/analysis`

The endpoint validates match context for a future tactical-analysis request.

Until a validated dataset and tactical model are connected, it returns:

- `status: unavailable`
- `data_driven: false`
- an explicit reason
- the accepted, validated request

It must not return a field recommendation at this stage.