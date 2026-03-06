/**
 * Реэкспорт эндпоинтов для компонентов.
 * Использует ключ bi для совместимости (biEndpoints.bi).
 * Источник: ../js/endpoints.js (biModern для EndpointManager).
 */
import { biEndpoints as registryEndpoints } from '../../js/endpoints.js'

export const biEndpoints = {
    bi: registryEndpoints.biModern
};
