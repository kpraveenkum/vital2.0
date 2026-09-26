"""
transport_model.py

STAGE 4
2-D Advection + Diffusion Solver
"""

import numpy as np


class TransportModel:

    def __init__(
        self,
        grid,
        diffusion_coefficient=100.0
    ):

        self.grid = grid
        self.dx = grid.dx
        self.dy = grid.dy
        self.K = diffusion_coefficient

    def advection(
        self,
        concentration,
        u,
        v
    ):

        C = concentration

        dCdx = np.zeros_like(C)
        dCdy = np.zeros_like(C)

        if C.shape[1] > 2:

            interior = (
                slice(None),
                slice(1, -1)
            )

            dCdx[interior] = np.where(
                u[interior] >= 0,
                (
                    C[:, 1:-1] -
                    C[:, :-2]
                ) / self.dx,
                (
                    C[:, 2:] -
                    C[:, 1:-1]
                ) / self.dx
            )

        if C.shape[0] > 2:

            interior = (
                slice(1, -1),
                slice(None)
            )

            dCdy[interior] = np.where(
                v[interior] >= 0,
                (
                    C[1:-1, :] -
                    C[:-2, :]
                ) / self.dy,
                (
                    C[2:, :] -
                    C[1:-1, :]
                ) / self.dy
            )

        return -u * dCdx - v * dCdy

    def diffusion(self, concentration):

        C = concentration

        d2Cdx2 = np.zeros_like(C)
        d2Cdy2 = np.zeros_like(C)

        if C.shape[1] > 2:

            d2Cdx2[:, 1:-1] = (
                C[:, 2:]
                - 2.0 * C[:, 1:-1]
                + C[:, :-2]
            ) / self.dx ** 2

        if C.shape[0] > 2:

            d2Cdy2[1:-1, :] = (
                C[2:, :]
                - 2.0 * C[1:-1, :]
                + C[:-2, :]
            ) / self.dy ** 2

        return self.K * (
            d2Cdx2 + d2Cdy2
        )

    def calculate_tendency(
        self,
        concentration,
        u,
        v
    ):

        return (
            self.advection(
                concentration, u, v
            )
            +
            self.diffusion(
                concentration
            )
        )

    def update(
        self,
        concentration,
        u,
        v,
        dt
    ):

        tendency = self.calculate_tendency(
            concentration, u, v
        )

        new_concentration = (
            concentration + dt * tendency
        )

        return np.maximum(
            new_concentration, 0.0
        )
