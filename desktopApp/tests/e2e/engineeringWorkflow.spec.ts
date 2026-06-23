import { expect, test } from '@playwright/test'

test.describe('engineering workflow (mock mode)', () => {
  test('create task, submit input, and generate report', async ({ page }) => {
    await page.goto('/')

    await page.getByRole('button', { name: '+ New engineering task' }).click()

    await expect(page.getByRole('heading', { name: 'Pipe Thickness Calculation' })).toBeVisible()
    await expect(page.getByText('Engineering inputs')).toBeVisible()

    const npsField = page.getByRole('textbox').first()
    await npsField.fill('6')
    await page.getByRole('button', { name: 'Save' }).click()

    await expect(page.getByText('nominal pipe size', { exact: false })).toBeVisible()
    await expect(page.getByText('6')).toBeVisible()

    await page.getByRole('button', { name: 'Generate report' }).click()

    await expect(page.getByText('Generated', { exact: false })).toBeVisible({ timeout: 10_000 })
  })
})
