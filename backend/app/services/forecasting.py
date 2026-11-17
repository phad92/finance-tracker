import numpy as np
from app.schemas.forecasting import (
    GoalRequiredSavingsRequest,
    GoalRequiredSavingsResponse,
    MonteCarloPercentiles,
    MonteCarloRequest,
    MonteCarloResponse,
    MonteCarloYearPoint,
    ProjectionRequest,
    ProjectionResponse,
    YearlyProjectionPoint,
)


def calculate_wealth_projection(req: ProjectionRequest) -> ProjectionResponse:
    """
    Project month-by-month compound wealth growth with optional annual contribution step-up
    and calculate purchasing power under inflation.
    """
    monthly_return_rate = req.annual_return_rate / 12.0
    current_nominal = req.initial_amount
    total_contributions = req.initial_amount
    current_monthly_contrib = req.monthly_contribution

    yearly_trajectory = [
        YearlyProjectionPoint(
            year=0,
            nominal_wealth=round(current_nominal, 2),
            real_wealth_inflation_adjusted=round(current_nominal, 2),
            total_contributions=round(total_contributions, 2),
            total_investment_gains=0.0,
        )
    ]

    for year in range(1, req.investment_years + 1):
        for _ in range(12):
            # Add return on existing balance
            current_nominal += current_nominal * monthly_return_rate
            # Add monthly savings
            current_nominal += current_monthly_contrib
            total_contributions += current_monthly_contrib

        # Annual step up in contribution rate if configured
        if req.contribution_growth_rate > 0:
            current_monthly_contrib *= (1.0 + req.contribution_growth_rate)

        # Discount for inflation: Real Wealth = Nominal / (1 + inflation)^year
        inflation_discount = (1.0 + req.inflation_rate) ** year
        real_wealth = current_nominal / inflation_discount if inflation_discount > 0 else current_nominal

        total_gains = max(0.0, current_nominal - total_contributions)

        yearly_trajectory.append(
            YearlyProjectionPoint(
                year=year,
                nominal_wealth=round(current_nominal, 2),
                real_wealth_inflation_adjusted=round(real_wealth, 2),
                total_contributions=round(total_contributions, 2),
                total_investment_gains=round(total_gains, 2),
            )
        )

    final_point = yearly_trajectory[-1]

    return ProjectionResponse(
        initial_amount=req.initial_amount,
        final_nominal_wealth=final_point.nominal_wealth,
        final_real_wealth=final_point.real_wealth_inflation_adjusted,
        total_contributions=final_point.total_contributions,
        total_investment_gains=final_point.total_investment_gains,
        yearly_trajectory=yearly_trajectory,
    )


def calculate_required_monthly_savings(req: GoalRequiredSavingsRequest) -> GoalRequiredSavingsResponse:
    """
    Calculate the exact monthly contribution required to reach a future financial goal.
    Uses ordinary annuity future value calculations.
    """
    total_months = int(round(req.target_years * 12))
    if total_months <= 0:
        total_months = 1

    monthly_rate = req.expected_annual_return / 12.0

    # 1. Nominal calculation
    fv_current = req.current_amount * ((1.0 + monthly_rate) ** total_months)
    remaining_nominal_deficit = max(0.0, req.target_amount - fv_current)

    if monthly_rate > 0:
        annuity_factor = (((1.0 + monthly_rate) ** total_months) - 1.0) / monthly_rate
        required_monthly_nominal = remaining_nominal_deficit / annuity_factor if annuity_factor > 0 else 0.0
    else:
        required_monthly_nominal = remaining_nominal_deficit / total_months

    # 2. Inflation-adjusted target calculation
    target_inflation_adjusted = req.target_amount * ((1.0 + req.inflation_rate) ** req.target_years)
    remaining_adjusted_deficit = max(0.0, target_inflation_adjusted - fv_current)

    if monthly_rate > 0:
        required_monthly_adjusted = remaining_adjusted_deficit / annuity_factor if annuity_factor > 0 else 0.0
    else:
        required_monthly_adjusted = remaining_adjusted_deficit / total_months

    projected_contributions = req.current_amount + (required_monthly_nominal * total_months)
    projected_gains = max(0.0, req.target_amount - projected_contributions)

    return GoalRequiredSavingsResponse(
        target_amount=req.target_amount,
        current_amount=req.current_amount,
        target_years=req.target_years,
        required_monthly_savings_nominal=round(required_monthly_nominal, 2),
        required_monthly_savings_inflation_adjusted=round(required_monthly_adjusted, 2),
        projected_total_contributed=round(projected_contributions, 2),
        projected_total_growth=round(projected_gains, 2),
    )


def calculate_monte_carlo_simulation(req: MonteCarloRequest) -> MonteCarloResponse:
    """
    Run vectorized Monte Carlo simulations to model probabilistic wealth outcomes
    under market volatility (generating 5th, 25th, 50th, 75th, and 95th percentile paths).
    """
    total_months = req.investment_years * 12
    monthly_mean = req.expected_annual_return / 12.0
    monthly_vol = req.annual_volatility / np.sqrt(12.0)

    # Initialize simulation matrix: (num_simulations, total_months + 1)
    sim_wealth = np.zeros((req.num_simulations, total_months + 1))
    sim_wealth[:, 0] = req.initial_amount

    # Generate random monthly return shocks across all paths
    np.random.seed(42)  # Deterministic seed for reproducible testing
    monthly_returns = np.random.normal(monthly_mean, monthly_vol, (req.num_simulations, total_months))

    cumulative_contributions = req.initial_amount
    yearly_trajectory = [
        MonteCarloYearPoint(
            year=0,
            percentiles=MonteCarloPercentiles(
                p5=round(req.initial_amount, 2),
                p25=round(req.initial_amount, 2),
                p50=round(req.initial_amount, 2),
                p75=round(req.initial_amount, 2),
                p95=round(req.initial_amount, 2),
            ),
            total_contributions=round(req.initial_amount, 2),
        )
    ]

    for m in range(1, total_months + 1):
        r_m = monthly_returns[:, m - 1]
        sim_wealth[:, m] = sim_wealth[:, m - 1] * (1.0 + r_m) + req.monthly_contribution

        # At the end of each year
        if m % 12 == 0:
            year_idx = m // 12
            cumulative_contributions += req.monthly_contribution * 12
            year_vals = sim_wealth[:, m]

            p5, p25, p50, p75, p95 = np.percentile(year_vals, [5, 25, 50, 75, 95])
            yearly_trajectory.append(
                MonteCarloYearPoint(
                    year=year_idx,
                    percentiles=MonteCarloPercentiles(
                        p5=round(float(p5), 2),
                        p25=round(float(p25), 2),
                        p50=round(float(p50), 2),
                        p75=round(float(p75), 2),
                        p95=round(float(p95), 2),
                    ),
                    total_contributions=round(cumulative_contributions, 2),
                )
            )

    prob_reaching_goal = None
    if req.target_wealth_goal and req.target_wealth_goal > 0:
        final_wealths = sim_wealth[:, -1]
        successful_runs = np.sum(final_wealths >= req.target_wealth_goal)
        prob_reaching_goal = round(float(successful_runs / req.num_simulations) * 100.0, 1)

    return MonteCarloResponse(
        investment_years=req.investment_years,
        num_simulations=req.num_simulations,
        expected_annual_return=req.expected_annual_return,
        annual_volatility=req.annual_volatility,
        trajectory=yearly_trajectory,
        probability_of_reaching_goal=prob_reaching_goal,
        target_wealth_goal=req.target_wealth_goal,
    )


