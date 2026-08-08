import api from "./api";


export async function getMetrics(deviceId){

    const response = await api.get(
        `/devices/${deviceId}/metrics`
    );

    return response.data;

}
