import { expect, test } from '@playwright/test'

test.describe('engineering workflow (mock mode)', () => {
  test('create task, submit input, and hide report until workflow completes', async ({ page }) => {
    await page.goto('/')

    await page.getByRole('button', { name: /pipe thickness — line 200/i }).click()

    await expect(page.getByRole('heading', { name: 'Pipe Wall Thickness Design' })).toBeVisible()
    await expect(page.getByPlaceholder('Value…')).toBeVisible()

    const npsField = page.getByPlaceholder('Value…')
    await npsField.fill('6')
    await page.getByRole('button', { name: 'Submit' }).click()

    await expect(page.getByPlaceholder('Complete the fields below to continue.')).toBeVisible()

    await expect(page.getByRole('heading', { name: 'Engineering report' })).toHaveCount(0)
  })
})
