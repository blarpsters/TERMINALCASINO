import asyncio
from unittest.mock import patch

import pytest
from textual.widgets import Input, Static

from casino.main import ALL_GAMES, GameSelect, NameSelect, main


def test_name_validation_and_submission():
    async def check():
        app = NameSelect()
        async with app.run_test() as pilot:
            await pilot.press('enter')
            assert app.return_value is None
            assert str(app.query_one('#error', Static).render())
            app.query_one(Input).value = '  Ethan  '
            await pilot.click('#enter')
        assert app.return_value == 'Ethan'
    asyncio.run(check())


@pytest.mark.parametrize('index, game', list(enumerate(ALL_GAMES)))
def test_game_buttons(index, game):
    async def check():
        app = GameSelect('[Ethan]', 75)
        async with app.run_test(size=(40, 20)) as pilot:
            button = app.query_one(f'#game-{index}')
            button.scroll_visible(animate=False)
            await pilot.pause()
            await pilot.click(f'#game-{index}')
        assert app.return_value == game
    asyncio.run(check())


@pytest.mark.parametrize('app', [NameSelect(), GameSelect('Ethan')])
def test_escape_exits(app):
    async def check():
        async with app.run_test() as pilot:
            await pilot.press('escape')
        assert app.return_value is None
    asyncio.run(check())


def test_game_returns_with_same_account():
    contexts = []
    def game(ctx):
        contexts.append(ctx)
        ctx.account.balance -= 10
    with patch('casino.main.GameSelect.run', side_effect=[ALL_GAMES[0], ALL_GAMES[0], None]), \
         patch.dict('casino.main.GAME_HANDLERS', {ALL_GAMES[0]: game}), \
         patch('casino.main.clear_screen'), patch('casino.main.cprint'):
        main('Ethan')
    assert contexts[0] is contexts[1]
    assert contexts[0].account.balance == 80


def test_cancel_name_does_not_create_account():
    with patch('casino.main.NameSelect.run', return_value=None), \
         patch('casino.main.Account.generate') as generate:
        main()
    generate.assert_not_called()
