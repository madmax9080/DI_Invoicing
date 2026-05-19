import { apiFetch } from "../api.js";

export const BuyerService = {
    async createBuyer(payload) {
        return await apiFetch("/buyers/", {
            method: "POST",
            body: payload
        });
    },

    async getBuyers({
        skip = 0,
        limit = 100,
        search = ""
    } = {}) {
        const params = new URLSearchParams({
            skip,
            limit
        });
        if (search?.trim()) {
            params.append(
                "search",
                search.trim()
            );
        }
        return await apiFetch(
            `/buyers/?${params.toString()}`
        );
    },

    async getBuyerById(buyerId) {
        return await apiFetch(
            `/buyers/id/${buyerId}`
        );
    },

    async getBuyerByNTN(ntn) {
        return await apiFetch(
            `/buyers/ntn/${encodeURIComponent(ntn)}`
        );
    },

    async updateBuyer(
        buyerId,
        payload
    ) {
        return await apiFetch(
            `/buyers/${buyerId}`,
            {
                method: "PUT",
                body: payload
            }
        );
    },

    async deleteBuyer(buyerId) {
        return await apiFetch(
            `/buyers/${buyerId}`,
            {
                method: "DELETE"
            }
        );
    }
};