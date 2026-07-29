<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <p class="filter-note">{{ t('restocking.filterNote') }}</p>

      <div class="card budget-card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.budget.title') }}</h3>
        </div>
        <div class="budget-slider">
          <div class="budget-value">{{ formatCurrency(budget, currentCurrency) }}</div>
          <input
            type="range"
            class="slider"
            v-model.number="budget"
            :min="0"
            :max="100000"
            :step="1000"
            :aria-label="t('restocking.budget.label')"
          >
          <div class="slider-range-labels">
            <span>{{ formatCurrency(0, currentCurrency) }}</span>
            <span>{{ formatCurrency(100000, currentCurrency) }}</span>
          </div>
          <p class="budget-hint">{{ t('restocking.budget.hint') }}</p>
        </div>
      </div>

      <div class="stats-grid">
        <div class="stat-card info">
          <div class="stat-label">{{ t('restocking.stats.itemsRecommended') }}</div>
          <div class="stat-value">{{ recommended.length }}</div>
        </div>
        <div class="stat-card success">
          <div class="stat-label">{{ t('restocking.stats.totalCost') }}</div>
          <div class="stat-value">{{ formatCurrency(totalCost, currentCurrency) }}</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-label">{{ t('restocking.stats.remainingBudget') }}</div>
          <div class="stat-value">{{ formatCurrency(remainingBudget, currentCurrency) }}</div>
        </div>
        <div class="stat-card danger">
          <div class="stat-label">{{ t('restocking.stats.unfundedItems') }}</div>
          <div class="stat-value">{{ unfunded.length }}</div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommendations') }}</h3>
        </div>

        <div v-if="candidates.length === 0" class="empty-state">
          {{ t('restocking.noShortages') }}
        </div>
        <div v-else-if="recommended.length === 0" class="empty-state">
          {{ t('restocking.noRecommendations') }}
        </div>
        <template v-else>
          <div class="table-container">
            <table>
              <thead>
                <tr>
                  <th>{{ t('restocking.table.rank') }}</th>
                  <th>{{ t('restocking.table.sku') }}</th>
                  <th>{{ t('restocking.table.itemName') }}</th>
                  <th>{{ t('restocking.table.trend') }}</th>
                  <th>{{ t('restocking.table.onHand') }}</th>
                  <th>{{ t('restocking.table.forecastedDemand') }}</th>
                  <th>{{ t('restocking.table.orderQuantity') }}</th>
                  <th>{{ t('restocking.table.unitCost') }}</th>
                  <th>{{ t('restocking.table.lineTotal') }}</th>
                  <th>{{ t('restocking.table.leadTime') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(item, index) in recommended" :key="item.sku">
                  <td>{{ index + 1 }}</td>
                  <td><strong>{{ item.sku }}</strong></td>
                  <td>{{ translateProductName(item.name) }}</td>
                  <td>
                    <span :class="['badge', item.trend]">{{ t('trends.' + item.trend) }}</span>
                  </td>
                  <td>{{ item.quantityOnHand }}</td>
                  <td>{{ item.forecastedDemand }}</td>
                  <td><strong>{{ item.shortfall }}</strong></td>
                  <td>{{ formatCurrencyWithDecimals(item.unitCost, currentCurrency, 2) }}</td>
                  <td><strong>{{ formatCurrencyWithDecimals(item.lineTotalCents / 100, currentCurrency, 2) }}</strong></td>
                  <td>{{ t('restocking.days', { days: item.leadTimeDays }) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>

        <p v-if="adequatelyStockedCount > 0" class="adequately-stocked-note">
          {{ t('restocking.adequatelyStocked', { count: adequatelyStockedCount }) }}
        </p>
      </div>

      <div class="card" v-if="unfunded.length">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.unfunded') }}</h3>
        </div>
        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.itemName') }}</th>
                <th>{{ t('restocking.table.orderQuantity') }}</th>
                <th>{{ t('restocking.table.lineTotal') }}</th>
                <th>{{ t('restocking.table.shortBy') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in unfunded" :key="item.sku">
                <td><strong>{{ item.sku }}</strong></td>
                <td>{{ translateProductName(item.name) }}</td>
                <td>{{ item.shortfall }}</td>
                <td>{{ formatCurrencyWithDecimals(item.lineTotalCents / 100, currentCurrency, 2) }}</td>
                <td>{{ formatCurrencyWithDecimals(item.shortByCents / 100, currentCurrency, 2) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="unfunded-hint">
          {{ t('restocking.unfundedHint', { amount: formatCurrency(budgetForCheapestUnfunded, currentCurrency), item: cheapestUnfundedItemName }) }}
        </p>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.summary.title') }}</h3>
        </div>
        <div class="order-summary">
          <div class="summary-line">{{ t('restocking.summary.items', { count: recommended.length }) }}</div>
          <div class="summary-line">{{ formatCurrency(totalCost, currentCurrency) }}</div>
          <div class="summary-line">{{ t('restocking.summary.leadTime', { days: maxLeadTimeDays }) }}</div>
          <div class="summary-line">{{ t('restocking.summary.expectedDelivery', { date: expectedDeliveryDate }) }}</div>
        </div>

        <button
          class="place-order-btn"
          :disabled="recommended.length === 0 || submitting || lastSubmittedOrder !== null"
          @click="placeOrder"
        >
          {{ submitting ? t('restocking.placingOrder') : t('restocking.placeOrder') }}
        </button>

        <p v-if="submitError" class="submit-error">{{ submitError }}</p>

        <div v-if="lastSubmittedOrder" class="order-placed-banner">
          <div class="order-placed-title">{{ t('restocking.orderPlaced', { orderNumber: lastSubmittedOrder.order_number }) }}</div>
          <div class="order-placed-detail">
            {{ t('restocking.orderPlacedDetail', {
              count: lastSubmittedOrder.items.length,
              total: formatCurrency(lastSubmittedOrder.total_value, currentCurrency),
              date: formatDate(lastSubmittedOrder.expected_delivery)
            }) }}
          </div>
          <router-link to="/orders">{{ t('restocking.viewInOrders') }}</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue'
import { api } from '../api'
import { useFilters } from '../composables/useFilters'
import { useI18n } from '../composables/useI18n'
import { formatCurrency, formatCurrencyWithDecimals } from '../utils/currency'

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency, currentLocale, translateProductName } = useI18n()

    const loading = ref(true)
    const error = ref(null)
    const submitting = ref(false)
    const submitError = ref(null)
    const lastSubmittedOrder = ref(null)

    const forecasts = ref([])
    const inventoryItems = ref([])
    const leadTimes = ref({})

    const budget = ref(25000)

    const { selectedLocation, selectedCategory, getCurrentFilters } = useFilters()

    const loadData = async () => {
      try {
        loading.value = true
        error.value = null
        const filters = getCurrentFilters()

        const [forecastsData, inventoryData, leadTimesData] = await Promise.all([
          api.getDemandForecasts(),
          api.getInventory({
            warehouse: filters.warehouse,
            category: filters.category
          }),
          api.getRestockLeadTimes()
        ])

        forecasts.value = forecastsData
        inventoryItems.value = inventoryData
        leadTimes.value = leadTimesData
      } catch (err) {
        error.value = 'Failed to load restocking data: ' + err.message
      } finally {
        loading.value = false
      }
    }

    watch([selectedLocation, selectedCategory], () => {
      loadData()
    })

    // Clear the success banner once the recommendation set changes, which also
    // re-enables Place Order - guards against submitting the same order twice
    watch([budget, selectedLocation, selectedCategory], () => {
      lastSubmittedOrder.value = null
    })

    // Budget-independent candidates: forecast items with a shortfall
    const candidates = computed(() => {
      const invBySku = new Map(inventoryItems.value.map(item => [item.sku, item]))
      const result = []

      for (const f of forecasts.value) {
        const inv = invBySku.get(f.item_sku)
        if (!inv) continue
        if (f.forecasted_demand <= 0) continue

        const shortfall = f.forecasted_demand - inv.quantity_on_hand
        if (shortfall <= 0) continue

        const shortfallRatio = shortfall / f.forecasted_demand
        const leadTimeDays = leadTimes.value[inv.category] ?? 14
        const lineTotalCents = Math.round(shortfall * inv.unit_cost * 100)

        result.push({
          sku: f.item_sku,
          name: f.item_name,
          category: inv.category,
          warehouse: inv.warehouse,
          trend: f.trend,
          quantityOnHand: inv.quantity_on_hand,
          forecastedDemand: f.forecasted_demand,
          shortfall,
          unitCost: inv.unit_cost,
          lineTotalCents,
          leadTimeDays,
          shortfallRatio
        })
      }

      return result
    })

    const adequatelyStockedCount = computed(() => {
      const invBySku = new Map(inventoryItems.value.map(item => [item.sku, item]))
      let count = 0
      for (const f of forecasts.value) {
        const inv = invBySku.get(f.item_sku)
        if (!inv) continue
        const shortfall = f.forecasted_demand - inv.quantity_on_hand
        if (shortfall <= 0) count++
      }
      return count
    })

    const trendRank = { increasing: 0, stable: 1, decreasing: 2 }

    const rankedCandidates = computed(() => {
      return candidates.value.slice().sort((a, b) => {
        const trendDiff = trendRank[a.trend] - trendRank[b.trend]
        if (trendDiff !== 0) return trendDiff

        const ratioDiff = b.shortfallRatio - a.shortfallRatio
        if (ratioDiff !== 0) return ratioDiff

        const shortfallDiff = b.shortfall - a.shortfall
        if (shortfallDiff !== 0) return shortfallDiff

        return a.sku.localeCompare(b.sku)
      })
    })

    const allocation = computed(() => {
      let remaining = Math.round(budget.value * 100)
      const rec = []
      const skipped = []

      for (const c of rankedCandidates.value) {
        if (c.lineTotalCents <= remaining) {
          rec.push(c)
          remaining -= c.lineTotalCents
        } else {
          // Skip and continue rather than break - a cheaper candidate further
          // down the ranked list may still fit the remaining budget
          skipped.push(c)
        }
      }

      // Measure the gap against the FINAL remaining budget, not the running one.
      // Cheaper candidates can still be funded after an item is skipped, so a
      // skip-time figure would contradict the Remaining Budget shown to the user.
      const unf = skipped.map(c => ({ ...c, shortByCents: c.lineTotalCents - remaining }))

      return { recommended: rec, unfunded: unf, remainingCents: remaining }
    })

    const recommended = computed(() => allocation.value.recommended)
    const unfunded = computed(() => allocation.value.unfunded)

    const totalCost = computed(() => {
      return recommended.value.reduce((sum, i) => sum + i.lineTotalCents, 0) / 100
    })

    const remainingBudget = computed(() => allocation.value.remainingCents / 100)

    const maxLeadTimeDays = computed(() => {
      if (recommended.value.length === 0) return 0
      return Math.max(...recommended.value.map(i => i.leadTimeDays))
    })

    const expectedDeliveryDate = computed(() => {
      const date = new Date()
      date.setDate(date.getDate() + maxLeadTimeDays.value)
      return formatDate(date)
    })

    // Pick by shortByCents, NOT by line total. `remaining` shrinks as cheaper
    // candidates later in the ranked list get funded, so the item needing the
    // smallest budget increase is not always the cheapest one.
    const cheapestUnfunded = computed(() => {
      if (unfunded.value.length === 0) return null
      return unfunded.value.reduce((min, i) => i.shortByCents < min.shortByCents ? i : min, unfunded.value[0])
    })

    // What to raise the budget TO, not what the item costs - most of the budget
    // is already committed to the funded items
    const budgetForCheapestUnfunded = computed(() => {
      if (!cheapestUnfunded.value) return 0
      return budget.value + cheapestUnfunded.value.shortByCents / 100
    })

    const cheapestUnfundedItemName = computed(() => {
      if (!cheapestUnfunded.value) return ''
      return translateProductName(cheapestUnfunded.value.name)
    })

    function formatDate(dateInput) {
      const date = dateInput instanceof Date ? dateInput : new Date(dateInput)
      if (isNaN(date.getTime())) return ''
      const locale = currentLocale.value === 'ja' ? 'ja-JP' : 'en-US'
      return date.toLocaleDateString(locale, {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      })
    }

    const placeOrder = async () => {
      if (submitting.value) return
      submitting.value = true
      submitError.value = null
      try {
        const payload = {
          budget: budget.value,
          items: recommended.value.map(i => ({ sku: i.sku, quantity: i.shortfall }))
        }
        const created = await api.createRestockOrder(payload)
        lastSubmittedOrder.value = created
      } catch (err) {
        submitError.value = t('restocking.submitError')
        console.error(err)
      } finally {
        submitting.value = false
      }
    }

    onMounted(loadData)

    return {
      t,
      currentCurrency,
      loading,
      error,
      submitting,
      submitError,
      lastSubmittedOrder,
      budget,
      candidates,
      recommended,
      unfunded,
      adequatelyStockedCount,
      totalCost,
      remainingBudget,
      maxLeadTimeDays,
      expectedDeliveryDate,
      budgetForCheapestUnfunded,
      cheapestUnfundedItemName,
      translateProductName,
      formatCurrency,
      formatCurrencyWithDecimals,
      formatDate,
      placeOrder
    }
  }
}
</script>

<style scoped>
.filter-note {
  color: #64748b;
  font-size: 0.875rem;
  margin-bottom: 1.25rem;
}

.budget-card {
  padding-bottom: 1.5rem;
}

.budget-slider {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0 0.5rem;
}

.budget-value {
  font-size: 2.25rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.slider {
  width: 100%;
  max-width: 560px;
  -webkit-appearance: none;
  appearance: none;
  height: 6px;
  border-radius: 3px;
  background: #e2e8f0;
  outline: none;
  margin: 0.5rem 0;
}

.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #2563eb;
  cursor: pointer;
  border: 3px solid white;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}

.slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #2563eb;
  cursor: pointer;
  border: 3px solid white;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}

.slider-range-labels {
  display: flex;
  justify-content: space-between;
  width: 100%;
  max-width: 560px;
  color: #64748b;
  font-size: 0.813rem;
  font-weight: 500;
}

.budget-hint {
  color: #64748b;
  font-size: 0.875rem;
  margin-top: 0.5rem;
}

.empty-state {
  text-align: center;
  padding: 2rem;
  color: #64748b;
  font-size: 0.938rem;
}

.adequately-stocked-note {
  margin-top: 1rem;
  color: #64748b;
  font-size: 0.875rem;
  font-style: italic;
}

.unfunded-hint {
  margin-top: 1rem;
  color: #64748b;
  font-size: 0.875rem;
}

.order-summary {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1.25rem;
}

.summary-line {
  color: #334155;
  font-size: 0.938rem;
}

.place-order-btn {
  background: #2563eb;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-size: 0.938rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease;
}

.place-order-btn:hover:not(:disabled) {
  background: #1d4ed8;
}

.place-order-btn:disabled {
  background: #cbd5e1;
  cursor: not-allowed;
}

.submit-error {
  margin-top: 0.75rem;
  color: #991b1b;
  font-size: 0.875rem;
}

.order-placed-banner {
  margin-top: 1.25rem;
  padding: 1rem;
  background: #d1fae5;
  border: 1px solid #6ee7b7;
  border-radius: 8px;
}

.order-placed-title {
  font-weight: 700;
  color: #065f46;
  margin-bottom: 0.375rem;
}

.order-placed-detail {
  color: #065f46;
  font-size: 0.875rem;
  margin-bottom: 0.5rem;
}

.order-placed-banner a {
  color: #047857;
  font-weight: 600;
}
</style>
