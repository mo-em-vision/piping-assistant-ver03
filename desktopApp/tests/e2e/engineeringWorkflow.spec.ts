import { expect, test } from '@playwright/test'

test.describe('engineering workflow (mock mode)', () => {
  test('create task, submit input, and hide report until workflow completes', async ({ page }) => {
    await page.goto('/')

    await page.getByRole('button', { name: '+ New engineering task' }).click()

    await expect(page.getByRole('heading', { name: 'Pipe Thickness Calculation' })).toBeVisible()
    await expect(page.getByPlaceholder(/enter nominal pipe size/i)).toBeVisible()

    const npsField = page.getByPlaceholder(/enter nominal pipe size/i)
    await npsField.fill('6')
    await page.getByRole('button', { name: 'Submit' }).click()

    await expect(page.getByText('nominal pipe size', { exact: false })).toBeVisible()
    await expect(page.getByText('6')).toBeVisible()

    await expect(page.getByRole('heading', { name: 'Engineering report' })).toHaveCount(0)
  })
})
